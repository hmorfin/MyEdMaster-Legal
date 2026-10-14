import sys
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

_AI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

from langgraph.graph import StateGraph, END

from graph.state import LegalChatState
from graph.nodes import (
    rag_node,
    extraction_node,
    anonymization_node,
    reasoning_node,
    formatter_node,
)
from langchain_community.callbacks import get_openai_callback

from benchmark.dataset import BenchmarkCase
from config import settings

if settings.openai_api_key and "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key


def _run_ragas_eval(query: str, answer: str, contexts: list[str]) -> tuple[float, float]:
    if not answer or not contexts:
        return -1.0, -1.0
    try:
        from ragas import evaluate
        from datasets import Dataset

        try:
            from ragas.metrics import faithfulness as _faith, answer_relevancy as _relev
        except ImportError:
            from ragas.metrics import faithfulness as _faith, answer_relevance as _relev  # type: ignore

        ds = Dataset.from_dict({
            "question": [query],
            "answer":   [answer],
            "contexts": [contexts],
        })
        result = evaluate(ds, metrics=[_faith, _relev])
        df = result.to_pandas()
        faith = float(df.iloc[0].get("faithfulness", -1.0))
        relev_col = next((c for c in df.columns if "relevance" in c or "relevancy" in c), None)
        relev = float(df.iloc[0][relev_col]) if relev_col else -1.0
        return round(faith, 4), round(relev, 4)
    except Exception as exc:
        print(f"[RAGAS] Evaluation failed: {exc}")
        return -1.0, -1.0


@dataclass
class BenchmarkResult:
    case_id: str
    category: str
    description: str
    total_latency_ms: float
    node_latencies: dict = field(default_factory=dict)
    chunks_retrieved: int = 0
    chunks_above_threshold: int = 0
    chunk_scores: list = field(default_factory=list)
    mean_chunk_score: float = 0.0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    final_answer_length: int = 0
    has_error: bool = False
    error_msg: str | None = None
    faithfulness_score: float = -1.0
    answer_relevance_score: float = -1.0
    has_document_context: bool = False
    has_sa_context: bool = False
    has_conversation_history: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _timed(fn, name: str, timings: dict):
    def wrapper(state: LegalChatState) -> dict:
        t0 = time.perf_counter()
        result = fn(state)
        timings[name] = round((time.perf_counter() - t0) * 1000, 1)
        return result
    return wrapper


def _build_timed_graph(timings: dict):
    graph = StateGraph(LegalChatState)

    graph.add_node("rag",           _timed(rag_node,           "rag",           timings))
    graph.add_node("extraction",    _timed(extraction_node,    "extraction",    timings))
    graph.add_node("anonymization", _timed(anonymization_node, "anonymization", timings))
    graph.add_node("reasoning",     _timed(reasoning_node,     "reasoning",     timings))
    graph.add_node("formatter",     _timed(formatter_node,     "formatter",     timings))

    graph.set_entry_point("rag")
    graph.add_edge("rag",           "extraction")
    graph.add_edge("extraction",    "anonymization")
    graph.add_edge("anonymization", "reasoning")
    graph.add_edge("reasoning",     "formatter")
    graph.add_edge("formatter",     END)

    return graph.compile()


def _make_capture_wrapper(original_fn, capture_list: list):
    def wrapper(query_vector, top_k=5, **kwargs):
        results = original_fn(query_vector=query_vector, top_k=top_k, **kwargs)
        capture_list.clear()
        capture_list.extend(results)
        return results
    return wrapper


class BenchmarkRunner:
    def __init__(self):
        self._embedding_ready = False

    def setup(self) -> None:
        if self._embedding_ready:
            return
        print("[BENCHMARK] Loading embedding model...")
        from rag.embedder import embedder
        embedder.load()
        print(f"[BENCHMARK] Embedding model ready: {settings.legal_embedding_model}")
        self._embedding_ready = True

    def run(self, case: BenchmarkCase) -> BenchmarkResult:
        import rag.vector_store as _vs

        timings: dict = {}
        captured_chunks: list = []

        original_search = _vs.search_chunks
        _vs.search_chunks = _make_capture_wrapper(original_search, captured_chunks)

        initial_state: LegalChatState = {
            "user_id":                  case.user_id,
            "query":                    case.query,
            "chat_id":                  case.chat_id,
            "document_paths":           case.document_paths,
            "document_text":            "",
            "document_urls":            [],
            "user_context":             case.user_context,
            "conversation_history":     case.conversation_history,
            "primary_topic":            case.primary_topic,
            "self_assessment_context":  case.self_assessment_context,
            "conversation_summary":     case.conversation_summary,
            "knowledge_chunks":         [],
            "anon_query":               "",
            "anon_knowledge":           [],
            "anon_document":            "",
            "llm_response":             "",
            "final_answer":             "",
            "detected_topic":           None,
            "confidence_delta":         None,
            "error":                    None,
        }

        timed_graph = _build_timed_graph(timings)
        error_msg: str | None = None
        result_state: LegalChatState = dict(initial_state)  # type: ignore
        in_tok, out_tok, cost = 0, 0, 0.0

        t_start = time.perf_counter()
        try:
            with get_openai_callback() as cb:
                result_state = timed_graph.invoke(initial_state)
            in_tok = cb.prompt_tokens
            out_tok = cb.completion_tokens
            cost = cb.total_cost
        except Exception as exc:
            error_msg = str(exc)
        finally:
            _vs.search_chunks = original_search

        total_ms = round((time.perf_counter() - t_start) * 1000, 1)

        chunk_scores = [round(r.score, 4) for r in captured_chunks]
        chunks_above = sum(1 for s in chunk_scores if s > 0.75)
        mean_score = round(sum(chunk_scores) / len(chunk_scores), 4) if chunk_scores else 0.0

        has_error = bool(error_msg or result_state.get("error"))
        err_str = error_msg or result_state.get("error") or None

        faith_score, relev_score = -1.0, -1.0
        if not has_error:
            chunks_for_ragas = result_state.get("knowledge_chunks") or []
            faith_score, relev_score = _run_ragas_eval(
                case.query,
                result_state.get("final_answer", ""),
                chunks_for_ragas,
            )

        return BenchmarkResult(
            case_id=case.id,
            category=case.category,
            description=case.description,
            total_latency_ms=total_ms,
            node_latencies=dict(timings),
            chunks_retrieved=len(captured_chunks),
            chunks_above_threshold=chunks_above,
            chunk_scores=chunk_scores,
            mean_chunk_score=mean_score,
            estimated_input_tokens=in_tok,
            estimated_output_tokens=out_tok,
            estimated_cost_usd=round(cost, 6),
            final_answer_length=len(result_state.get("final_answer", "")),
            has_error=has_error,
            error_msg=err_str,
            has_document_context=bool(case.document_paths),
            has_sa_context=bool(case.self_assessment_context),
            has_conversation_history=bool(case.conversation_history),
            model=settings.openai_model,
            faithfulness_score=faith_score,
            answer_relevance_score=relev_score,
        )
