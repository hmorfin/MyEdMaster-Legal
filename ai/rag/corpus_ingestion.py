# ai/rag/corpus_ingestion.py
import logging
import os
import uuid
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from bs4 import BeautifulSoup
from datetime import datetime

from config import settings
from document_extraction.extractor import extractor
from rag.embedder import embed_texts, EMBEDDING_DIM
from rag.vector_store import ensure_collection, upsert_chunks
from  openai import OpenAI

logger = logging.getLogger(__name__)

openai = OpenAI(api_key=settings.openai_api_key)


_llm_client = OpenAI(api_key=settings.openai_api_key)

BASE_DIR = Path(__file__).resolve().parents[1]  # points to ai/
CORPUS_ROOT = BASE_DIR / "data" / "corpus"
CASE_LAW_DIR = CORPUS_ROOT / "case_law"
CONTRACTS_DIR = CORPUS_ROOT / "contracts"


def extract_pdf_text(path: Path) -> str:
    return extractor.extract_from_path(str(path))


def extract_html_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")


def normalize_text(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    chunks: List[str] = []
    n = len(text)
    if n == 0:
        return chunks

    start = 0
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

total_input_tokens = 0
total_output_tokens = 0

def _call_llm_json(system: str, user: str) -> dict:
    global total_input_tokens, total_output_tokens
    try:
        resp = _llm_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user + "\n\nRespond with a valid JSON object only."},
            ],
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        usage = resp.usage
        total_input_tokens += usage.prompt_tokens
        total_output_tokens += usage.completion_tokens

        return json.loads(resp.choices[0].message.content)
    except Exception:
        logger.warning("corpus_llm_classification_failed", exc_info=True)
        return {}

def classify_contract_type_and_date(full_text: str) -> tuple[Optional[str], Optional[str]]:
    snippet = full_text[:3000]
    system = "You classify contracts by type and effective date."
    user = (
        "Return a JSON object with exactly these keys:\n"
        '"contract_type": short label such as "Master Services Agreement", '
        '"NDA", "Purchase Agreement", "License Agreement", "Employment Agreement", "Other".\n'
        '"contract_date": effective date in ISO format YYYY-MM-DD if you can find it, else null.\n\n'
        f"Snippet:\n{snippet}"
    )
    data = _call_llm_json(system, user)
    return data.get("contract_type"), data.get("contract_date")



def extract_case_title_and_date(full_text: str) -> Tuple[Optional[str], Optional[str]]:
    snippet = full_text[:3000]
    system = "You extract case law titles and decision dates."
    user = (
        "From the legal case snippet, return JSON with:\n"
        "  case_title: full case name if you can identify it.\n"
        "  case_date: decision date in ISO format YYYY-MM-DD if mentioned, else null.\n\n"
        f"Snippet:\n{snippet}"
    )
    data = _call_llm_json(system, user)
    return data.get("case_title"), data.get("case_date")


def build_points_for_file(path: Path, doc_type: str) -> List[Dict]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        raw = extract_pdf_text(path)
    elif ext in {".html", ".htm"}:
        raw = extract_html_text(path)
    else:
        logger.warning("corpus_unsupported_file_type_skipped", extra={"extension": ext})
        return []

    normalized = normalize_text(raw)
    text_chunks = chunk_text(normalized)
    if not text_chunks:
        logger.warning("corpus_file_produced_no_chunks", extra={"file_name": path.name})
        return []

    contract_type = contract_date = None
    case_title = case_date = None

    if doc_type == "contract":
        contract_type, contract_date = classify_contract_type_and_date(normalized)
    elif doc_type == "case_law":
        case_title, case_date = extract_case_title_and_date(normalized)

    embeddings = embed_texts(text_chunks)
    if len(embeddings) != len(text_chunks):
        raise RuntimeError("Embedding count does not match chunk count")

    doc_id = str(uuid.uuid4())
    title = path.stem

    # Generate a numeric base per document so IDs are unique in this batch
    base_id = uuid.uuid4().int % 1_000_000_000

    points: List[Dict] = []
    for idx, (chunk_text_content, vec) in enumerate(zip(text_chunks, embeddings)):
        point_id = base_id + idx  # integer ID, OK for Qdrant

        payload = {
            "doc_id": doc_id,
            "chunk_id": idx,
            "doc_type": doc_type,
            "case_title": case_title,
            "case_date": case_date,
            "contract_type": contract_type,
            "contract_date": contract_date,
            "title": title,
            "source_path": str(path),
            "text": chunk_text_content,
        }
        points.append(
            {
                "id": point_id,
                "vector": vec,
                "payload": payload,
            }
        )
    return points


def ingest_directory(root_dir: Path, doc_type: str) -> None:
    ensure_collection(vector_size=EMBEDDING_DIM)

    files_processed = 0
    chunks_ingested = 0
    all_points: List[Dict] = []
    for root, _, files in os.walk(root_dir):
        for fname in files:
            path = Path(root) / fname
            logger.info("corpus_ingesting_file", extra={"doc_type": doc_type, "file_name": fname})
            points = build_points_for_file(path, doc_type=doc_type)
            all_points.extend(points)
            files_processed += 1

            if len(all_points) >= 200:
                upsert_chunks(all_points)
                chunks_ingested += len(all_points)
                all_points = []

    if all_points:
        upsert_chunks(all_points)
        chunks_ingested += len(all_points)

    logger.info(
        "corpus_ingest_directory_completed",
        extra={"doc_type": doc_type, "files_processed": files_processed, "chunks_ingested": chunks_ingested},
    )


def ingest_case_law_directory() -> None:
    ingest_directory(CASE_LAW_DIR, doc_type="case_law")


def ingest_contracts_directory() -> None:
    ingest_directory(CONTRACTS_DIR, doc_type="contract")


if __name__ == "__main__":
    from logging_config import configure_logging

    configure_logging()
    logger.info(
        "corpus_ingestion_starting",
        extra={"case_law_dir": str(CASE_LAW_DIR), "contracts_dir": str(CONTRACTS_DIR)},
    )
    ingest_case_law_directory()
    ingest_contracts_directory()
    logger.info(
        "corpus_ingestion_completed",
        extra={"total_input_tokens": total_input_tokens, "total_output_tokens": total_output_tokens},
    )