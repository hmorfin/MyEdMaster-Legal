import logging
from .preprocessingUtilityFunctions import (
    sanitize_input,
    fetch_user_context,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preprocess_query(user_id: int, conversation_id: int, user_query: str) -> dict:
    logger.info(f"Starting preprocessing for user_id={user_id}")

    # Step 1: Sanitize input
    step1 = sanitize_input(user_query)
    if not step1["success"]:
        logger.error(f"Sanitization failed: {step1['error']}")
        return step1

    cleaned_query = step1["data"]
    logger.info("Step 1 complete: Input sanitized")

    # Step 2: Fetch user context
    step2 = fetch_user_context(user_id, conversation_id)
    if not step2["success"]:
        logger.error(f"Context fetch failed: {step2['error']}")
        return step2

    user_context = step2["data"]
    logger.info(f"Step 2 complete: User context fetched (level={user_context['knowledge_level']})")

    return {
        "success": True,
        "error": None,
        "data": {
            "cleaned_query": cleaned_query,
            "user_context": user_context,
            "metadata": {
                "user_id": user_id,
                "conversation_id": conversation_id,
            }
        }
    }