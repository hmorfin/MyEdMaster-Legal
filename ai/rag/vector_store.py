# ai/rag/vector_store.py
import logging
import time
from typing import Iterable, List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from config import settings

logger = logging.getLogger(__name__)


def get_qdrant_client() -> QdrantClient:
    if settings.qdrant_api_key:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(vector_size: int | None = None) -> None:
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection
    vector_size = vector_size or settings.embedding_dim

    if collection_name in [c.name for c in client.get_collections().collections]:
        return

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )
    create_payload_indexes()


def upsert_chunks(chunks: Iterable[Dict[str, Any]]) -> None:
    chunks = list(chunks)
    if not chunks:
        return

    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    points: List[PointStruct] = []
    for ch in chunks:
        points.append(
            PointStruct(
                id=ch["id"],
                vector=ch["vector"],
                payload=ch["payload"],
            )
        )

    start = time.time()
    client.upsert(
        collection_name=collection_name,
        points=points,
        wait=True,
    )
    logger.info(
        "qdrant_upsert_completed",
        extra={
            "collection": collection_name,
            "points_count": len(points),
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )


def delete_by_doc_id(doc_id: str) -> None:
    client = get_qdrant_client()

    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
            ]
        ),
        wait=True,
    )
    logger.info(
        "qdrant_delete_by_doc_id_completed",
        extra={"collection": settings.qdrant_collection, "doc_id": doc_id},
    )



def create_payload_indexes() -> None:
    """Create indexes on filterable payload fields — required by Qdrant for filtered search."""
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    for field in ["doc_id", "doc_type", "contract_type", "case_title"]:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema="keyword",
        )


def search_chunks(
    query_vector: List[float],
    top_k: int = 5,
    doc_type: Optional[str] = None,
    contract_type: Optional[str] = None,
    case_title: Optional[str] = None,
    ) -> List[Any]:
    client = get_qdrant_client()
    conditions = []
    if doc_type is not None:
        conditions.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))
    if contract_type is not None:
        conditions.append(FieldCondition(key="contract_type", match=MatchValue(value=contract_type)))
    if case_title is not None:
        conditions.append(FieldCondition(key="case_title", match=MatchValue(value=case_title)))

    qdrant_filter = Filter(must=conditions) if conditions else None

    start = time.time()
    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    logger.info(
        "qdrant_search_completed",
        extra={
            "collection": settings.qdrant_collection,
            "top_k": top_k,
            "filters_applied": len(conditions),
            "results_count": len(results.points),
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )

    return results.points