# ai/routers/query.py
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rag.embedder import embed_texts
from rag.vector_store import search_chunks

from graph.builder import legal_graph
from graph.state import LegalChatState
from graph.nodes import run_summarization

logger = logging.getLogger(__name__)
router = APIRouter()




# ---------------------------------------------------------------------------
# Schemas — Direct vector search (new endpoint)
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language question to search for")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to return")

    # --- Optional metadata pre-filters (all ANDed together) ---
    # Pass only the filters you need; omit the rest.
    doc_type: Optional[str] = Field(
        default=None,
        description="Filter by document category: 'contract' or 'case_law'",
    )
    contract_type: Optional[str] = Field(
        default=None,
        description="Filter by contract type e.g. 'NDA', 'Master Services Agreement'",
    )
    case_title: Optional[str] = Field(
        default=None,
        description="Filter by case title (must be an exact match to the stored value)",
    )


class ChunkResult(BaseModel):
    score: float = Field(..., description="Cosine similarity score (0–1, higher is better)")
    doc_id: str
    chunk_id: int
    doc_type: str
    title: str
    text: str

    # Contract-specific (null for case law)
    contract_type: Optional[str] = None
    contract_date: Optional[str] = None

    # Case-law-specific (null for contracts)
    case_title: Optional[str] = None
    case_date: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[ChunkResult]


# ---------------------------------------------------------------------------
# POST /query  (existing — LangGraph chat flow)
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    user_id: str
    query: str
    chat_id: str | None = None
    user_context: dict = {}
    conversation_history: list = []
    primary_topic: str | None = None
    document_paths: list[str] = []
    self_assessment_context: dict = {}
    conversation_summary: str | None = None
    mode: str = "chat"
    document_context: dict = {}


class QueryResponse(BaseModel):
    answer: str
    has_document_context: bool
    has_knowledge_context: bool
    document_urls:        list[str]  = []
    detected_topic: list[str] | None = None
    confidence_delta: float | None = None
    conversation_summary: str | None = None
    ready_to_generate: bool = False
    document_context: dict = {}
    knowledge_sources: list[dict] = []

@router.post("", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(
        "query_received",
        extra={
            "user_id": request.user_id,
            "chat_id": request.chat_id,
            "query_length": len(request.query),
            "document_count": len(request.document_paths),
            "mode": request.mode,
            "has_self_assessment_context": bool(request.self_assessment_context),
            "conversation_history_length": len(request.conversation_history),
        },
    )

    initial_state: LegalChatState = {
        "user_id":          request.user_id,
        "query":            request.query,
        "chat_id": request.chat_id,
        "document_paths":   request.document_paths,
        "document_text":    "",
        "user_context": request.user_context,
        "conversation_history": request.conversation_history,
        "primary_topic": request.primary_topic,
        "document_urls":    [],
        "knowledge_chunks": [],
        "knowledge_sources": [],
        "anon_query":       "",
        "anon_knowledge":   [],
        "anon_document":    "",
        "llm_response":     "",
        "final_answer":     "",
        "detected_topic": None,
        "confidence_delta": None,
        "error":            None,
        "self_assessment_context": request.self_assessment_context,
        "conversation_summary": request.conversation_summary,
        "mode": request.mode,
        "document_context": request.document_context,
        "ready_to_generate": False,
    }

    try:
        result: LegalChatState = legal_graph.invoke(initial_state)
    except Exception as e:
        logger.error(
            "query_graph_execution_failed",
            exc_info=True,
            extra={"user_id": request.user_id, "chat_id": request.chat_id},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Graph execution failed: {str(e)}",
        )

    logger.info(
        "query_completed",
        extra={
            "user_id": request.user_id,
            "chat_id": request.chat_id,
            "knowledge_chunks_used": len(result.get("knowledge_chunks", [])),
            "has_error": bool(result.get("error")),
            "answer_length": len(result.get("final_answer") or ""),
        },
    )

    return QueryResponse(
        answer=result["final_answer"],
        has_document_context=bool(result.get("document_text")),
        has_knowledge_context=bool(result.get("anon_knowledge")),
        detected_topic=result.get("detected_topic"),
        confidence_delta=result.get("confidence_delta"),
        document_urls=result.get("document_urls", []),
        conversation_summary=result.get("conversation_summary"),
        ready_to_generate=result.get("ready_to_generate", False),
        document_context=result.get("document_context", {}),
        knowledge_sources=result.get("knowledge_sources", []),
    )


class SummarizeRequest(BaseModel):
    messages: list
    existing_summary: str | None = None


class SummarizeResponse(BaseModel):
    summary: str


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest):
    logger.info(
        "summarize_requested",
        extra={"messages_count": len(request.messages), "has_existing_summary": bool(request.existing_summary)},
    )
    try:
        summary = run_summarization(
            messages=request.messages,
            existing_summary=request.existing_summary,
        )
        return SummarizeResponse(summary=summary)
    except Exception as e:
        logger.error("summarization_failed", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}",
        )

# ---------------------------------------------------------------------------
# POST /query/search  (new — direct Qdrant semantic search with filters)
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Embed the query and run a filtered semantic search directly against Qdrant.

    This endpoint bypasses the LangGraph pipeline and is useful for:
      - Debugging what chunks are being retrieved for a query
      - Building a "browse corpus" UI feature
      - Letting the frontend filter by doc_type / contract_type / case_title

    Metadata filters are applied *before* vector search (Qdrant pre-filtering),
    so only matching documents are candidates — this is fast and accurate.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(
        "direct_search_requested",
        extra={
            "query_length": len(request.query),
            "top_k": request.top_k,
            "doc_type": request.doc_type,
            "contract_type": request.contract_type,
        },
    )

    # Embed the query using the same model used during ingestion
    vectors = embed_texts([request.query])
    if not vectors:
        logger.error("direct_search_embedding_failed")
        raise HTTPException(status_code=500, detail="Failed to embed the query.")

    query_vector = vectors[0]

    scored_points = search_chunks(
        query_vector=query_vector,
        top_k=request.top_k,
        doc_type=request.doc_type,
        contract_type=request.contract_type,
        case_title=request.case_title,
    )
    logger.info("direct_search_completed", extra={"results_count": len(scored_points)})

    results: List[ChunkResult] = []
    for point in scored_points:
        p = point.payload  # everything stored at ingest time
        results.append(
            ChunkResult(
                score=round(point.score, 4),
                doc_id=p.get("doc_id", ""),
                chunk_id=p.get("chunk_id", 0),
                doc_type=p.get("doc_type", ""),
                title=p.get("title", ""),
                text=p.get("text", ""),
                contract_type=p.get("contract_type"),
                contract_date=p.get("contract_date"),
                case_title=p.get("case_title"),
                case_date=p.get("case_date"),
            )
        )

    return SearchResponse(query=request.query, results=results)