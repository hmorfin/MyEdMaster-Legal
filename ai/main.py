import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from logging_config import configure_logging, request_id_ctx_var

configure_logging()
logger = logging.getLogger(__name__)

from config import settings

from routers import ingest, query, courses, fspr, documents
from self_assessment.router import router as self_assessment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ai_service_starting", extra={"embedding_model": settings.legal_embedding_model})
    from rag.embedder import embedder
    embedder.load()
    logger.info("embedding_model_ready", extra={"embedding_model": settings.legal_embedding_model})
    yield
    logger.info("ai_service_shutting_down")


app = FastAPI(
    title="Legal Chatbot — AI Service",
    description=(
        "Internal FastAPI service powering the LangGraph AI layer. "
        "Handles legal knowledge retrieval, document extraction, "
        "PII anonymization, and LLM reasoning."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# --- Request logging middleware ---
# Assigns a short request_id to every inbound request (reusing X-Request-ID if the
# caller — e.g. the Django backend — already set one), attaches it to every log line
# emitted while handling the request via a contextvar, and logs one summary line per
# request. Never logs request/response bodies — those may contain user queries,
# document text, or PII.
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_ctx_var.set(request_id)
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed",
            extra={"method": request.method, "path": request.url.path},
        )
        raise
    else:
        duration_ms = round((time.time() - start) * 1000, 1)
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx_var.reset(token)


# --- Routers ---
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(self_assessment_router, prefix="/self-assessment", tags=["Self Assessment"])
app.include_router(courses.router, prefix="/learning", tags=["Learning"])
app.include_router(fspr.router, prefix="/fspr", tags=["FSPR"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])


# --- Health check ---
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "embedding_model": settings.legal_embedding_model,
        "llm_model": settings.openai_model,
    }