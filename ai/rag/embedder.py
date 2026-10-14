import logging
import time

from sentence_transformers import SentenceTransformer
from config import settings

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self):
        self._model: SentenceTransformer | None = None

    def load(self):
        if self._model is None:
            start = time.time()
            logger.info("embedding_model_loading", extra={"model": settings.legal_embedding_model})
            self._model = SentenceTransformer(settings.legal_embedding_model)
            logger.info(
                "embedding_model_loaded",
                extra={
                    "model": settings.legal_embedding_model,
                    "duration_ms": round((time.time() - start) * 1000, 1),
                },
            )

    def _ensure_loaded(self):
        if self._model is None:
            self._model = SentenceTransformer(settings.legal_embedding_model)

    def embed(self, text: str) -> list[float]:
        self._ensure_loaded()
        vector = self._model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        start = time.time()
        vectors = self._model.encode(texts, convert_to_numpy=True, batch_size=32)
        logger.info(
            "embedding_batch_completed",
            extra={"batch_size": len(texts), "duration_ms": round((time.time() - start) * 1000, 1)},
        )
        return vectors.tolist()

    @property
    def dimension(self) -> int:
        self._ensure_loaded()
        return self._model.get_sentence_embedding_dimension()


embedder = Embedder()


# ---------------------------------------------------------------------------
# Compatibility shims for corpus_ingestion.py
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 768

def embed_texts(texts: list[str]) -> list[list[float]]:
    return embedder.embed_batch(texts)