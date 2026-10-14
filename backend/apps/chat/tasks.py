import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_summarization_task(self, chat_id, messages_to_summarize, existing_summary, cutoff_message_id):
    try:
        from django.db import close_old_connections
        from apps.chat.models import Conversation
        import ai_client

        close_old_connections()

        result = ai_client.summarize(
            messages=messages_to_summarize,
            existing_summary=existing_summary,
        )
        new_summary = result.get("summary")
        if new_summary:
            try:
                conv = Conversation.objects.get(id=chat_id)
                conv.conversation_summary = new_summary
                conv.last_summarized_message_id = cutoff_message_id
                conv.save(update_fields=["conversation_summary", "last_summarized_message_id", "updated_at"])
                logger.info(f"[SUMMARIZATION] Persisted new summary for chat {chat_id}")
            except Conversation.DoesNotExist:
                logger.warning(f"[SUMMARIZATION] Conversation {chat_id} deleted before summary could be saved")
    except Exception as exc:
        logger.error(f"[SUMMARIZATION] Task failed: {exc}")
        raise self.retry(exc=exc)