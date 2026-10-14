# ai/routers/ingest.py
import logging
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from rag.corpus_ingestion import build_points_for_file
from rag.embedder import EMBEDDING_DIM
from rag.vector_store import delete_by_doc_id, ensure_collection, upsert_chunks

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".html", ".htm"}
_ALLOWED_DOC_TYPES = {"contract", "case_law"}



# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    doc_type: str
    chunks_ingested: int
    message: str


class DeleteResponse(BaseModel):
    doc_id: str
    message: str


# ---------------------------------------------------------------------------
# POST /ingest/upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=IngestResponse, status_code=201)
async def upload_and_ingest(
    file: UploadFile = File(..., description="PDF or HTML document to ingest"),
    doc_type: str = Form(..., description="Document category: 'contract' or 'case_law'"),
):
    """
    Upload a single PDF or HTML file and ingest it into the Qdrant vector store.

    The file is:
      1. Saved to a temp location on disk.
      2. Parsed, chunked, classified (via LLM), and embedded — reusing the exact
         same pipeline that bulk-ingestion uses (build_points_for_file).
      3. Upserted into Qdrant under a freshly generated doc_id.

    Returns the doc_id so the caller can reference or delete the document later.
    """
    # --- Validate doc_type ---
    if doc_type not in _ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type must be one of {sorted(_ALLOWED_DOC_TYPES)}",
        )

    # --- Validate file extension ---
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    start = time.time()
    logger.info(
        "document_ingest_requested",
        extra={"doc_type": doc_type, "file_extension": suffix},
    )

    # --- Write upload to a temp file (build_points_for_file needs a real Path) ---
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        # --- Run the same ingestion pipeline used for bulk ingestion ---
        ensure_collection(vector_size=EMBEDDING_DIM)
        points = build_points_for_file(tmp_path, doc_type=doc_type)

        if not points:
            logger.warning("document_ingest_no_text_extracted", extra={"doc_type": doc_type})
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the uploaded file.",
            )

        upsert_chunks(points)

        # doc_id is identical across all chunks for the same file
        doc_id: str = points[0]["payload"]["doc_id"]

        logger.info(
            "document_ingest_completed",
            extra={
                "doc_id": doc_id,
                "doc_type": doc_type,
                "chunks_ingested": len(points),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )

        return IngestResponse(
            doc_id=doc_id,
            filename=file.filename,
            doc_type=doc_type,
            chunks_ingested=len(points),
            message=f"Successfully ingested {len(points)} chunks into the vector store.",
        )

    finally:
        # Always clean up the temp file, even on error
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# DELETE /ingest/{doc_id}
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}", response_model=DeleteResponse)
def delete_document(doc_id: str):
    """
    Remove every chunk belonging to a document from the Qdrant collection.

    All chunks share the same payload.doc_id (set during ingestion), so this
    deletes the complete document in a single Qdrant filter-delete call.

    The doc_id is returned by the /upload endpoint — store it if you need to
    support deletion later.
    """
    if not doc_id.strip():
        raise HTTPException(status_code=400, detail="doc_id cannot be empty.")

    delete_by_doc_id(doc_id)
    logger.info("document_deleted", extra={"doc_id": doc_id})

    return DeleteResponse(
        doc_id=doc_id,
        message=f"All chunks for doc_id '{doc_id}' have been deleted from the vector store.",
    )