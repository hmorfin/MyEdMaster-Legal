import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class VectorDbNotConfigured(Exception):
    pass


def get_vector_db_client():
    """
    Returns an authenticated client for the vector DB.
    Raises VectorDbNotConfigured if required config is missing.
    """
    if not settings.VECTOR_DB_URL or not settings.VECTOR_DB_API_KEY:
        logger.error("Vector DB config missing: URL or API key not set")
        raise VectorDbNotConfigured("Vector DB is not configured correctly")

    # TODO: replace this stub with actual client implementation
    # Example structure so the rest of the code can call client methods:
    class DummyVectorClient:
        def __init__(self, url, port, api_key):
            self.url = url
            self.port = port
            self.api_key = api_key

        def health_check(self):
            # later: real ping to vector DB
            return True

    return DummyVectorClient(
        url=settings.VECTOR_DB_URL,
        port=settings.VECTOR_DB_PORT,
        api_key=settings.VECTOR_DB_API_KEY,
    )


def check_vector_db_health():
    """
    Returns True if vector DB is reachable, False otherwise.
    For now, uses the client's health_check stub.
    """
    try:
        client = get_vector_db_client()
        return bool(client.health_check())
    except VectorDbNotConfigured:
        # treat "not configured" as unhealthy for the health endpoint
        return False
    except Exception as exc:
        logger.exception("Vector DB health check failed: %s", exc)
        return False
