import bleach
import tiktoken
import re
from django.core.exceptions import ObjectDoesNotExist
from bson import ObjectId
from apps.users.models import UserProfile
from .models import TopicMastery, Conversation, Message
from datetime import date

MAX_QUERY_LENGTH = 1000
SUMMARY_TOKEN_THRESHOLD = 1500
RECENT_MESSAGE_COUNT = 6

# get the age range from dob (age range is more suitable for queries)
def get_age_range(dob) -> str:
    if not dob:
        return ""
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18: return "under-18"
    elif age < 25: return "18-24"
    elif age < 35: return "25-34"
    elif age < 45: return "35-44"
    elif age < 55: return "45-54"
    elif age < 65: return "55-64"
    else: return "65+"

def sanitize_input(user_query: str) -> dict:
    """
    Clean and validate user input for security and cost protection.

    Args:
        user_query: Raw string from user interface

    Returns:
        Dictionary with success status and cleaned query or error message
    """

    user_query = re.sub(r'<script[^>]*>.*?</script>', '', user_query, flags=re.IGNORECASE | re.DOTALL)
    # Strip HTML and script tags (security)
    cleaned = bleach.clean(user_query, tags=[], strip=True)

    # Enforce character limit (cost protection)
    if len(cleaned) > MAX_QUERY_LENGTH:
        return {
            "success": False,
            "error": "Your question is too long. Please keep it under 1000 characters.",
            "data": None
        }

    return {
        "success": True,
        "error": None,
        "data": cleaned
    }


def fetch_user_context(user_id: int, conversation_id: int) -> dict:
    """
    Retrieve user profile and conversation data from database.

    Args:
        user_id: Database ID of the user
        conversation_id: Database ID of the conversation

    Returns:
        Dictionary with user context data or error message
    """

    # Fetch user profile from apps.users
    try:
        user = UserProfile.objects.get(id=ObjectId(str(user_id)))
    except ObjectDoesNotExist:
        return {
            "success": False,
            "error": "User not found.",
            "data": None
        }

    # Extract preprocessing fields from user_attributes JSON field
    attrs = user.user_attributes or {}
    location = user.location or {}

    # Fetch topic mastery scores
    mastery_scores = TopicMastery.objects.filter(
        user_id=user_id
    ).values('topic', 'mastery_level')

    mastery_map = {
        item['topic']: item['mastery_level']
        for item in mastery_scores
    } if mastery_scores.exists() else {}

    try:
        conversation = Conversation.objects.get(id=ObjectId(str(conversation_id)))

        # Fetch messages since last summarization point, or all if never summarized
        last_id = conversation.last_summarized_message_id
        if last_id:
            try:
                cutoff_msg = Message.objects.get(id=ObjectId(last_id))
                messages_qs = Message.objects.filter(
                    conversation_id=conversation_id,
                    created_at__gt=cutoff_msg.created_at,
                ).order_by('created_at')
            except Message.DoesNotExist:
                messages_qs = Message.objects.filter(
                    conversation_id=conversation_id,
                ).order_by('created_at')
        else:
            messages_qs = Message.objects.filter(
                conversation_id=conversation_id,
            ).order_by('created_at')

        all_messages = list(messages_qs)

        # Check summarization threshold
        encoding = tiktoken.get_encoding("cl100k_base")
        total_tokens = sum(len(encoding.encode(m.content)) for m in all_messages)

        needs_summarization = False
        messages_to_summarize = []

        if total_tokens > SUMMARY_TOKEN_THRESHOLD and len(all_messages) > RECENT_MESSAGE_COUNT:
            recent_msgs = all_messages[-RECENT_MESSAGE_COUNT:]
            older_msgs = all_messages[:-RECENT_MESSAGE_COUNT]
            needs_summarization = True
            messages_to_summarize = [
                {"role": m.role, "content": m.content, "id": str(m.id)}
                for m in older_msgs
            ]
            cutoff_message_id = str(older_msgs[-1].id)
        else:
            recent_msgs = all_messages[-RECENT_MESSAGE_COUNT:]
            cutoff_message_id = None

        history = []
        historical_document_paths = []

        for message in recent_msgs:
            history.append({
                "role": message.role,
                "content": message.content,
            })
            if message.role == "user" and message.document_paths:
                for path in message.document_paths:
                    if path not in historical_document_paths:
                        historical_document_paths.append(path)

    except ObjectDoesNotExist:
        history = []
        historical_document_paths = []
        needs_summarization = False
        messages_to_summarize = []
        cutoff_message_id = None
        conversation = None

    # Return user context
    return {
        "success": True,
        "error": None,
        "data": {
            "user_id": user_id,
            "knowledge_level": attrs.get("knowledge_level", "beginner"),
            "jurisdiction": location.get("state", "Federal"),
            "county": location.get("county", ""),
            "age_range": get_age_range(user.dob),
            "is_minor": get_age_range(user.dob) == "under-18",
            "veteran_status": attrs.get("veteran_status", "Not a Veteran") == "Veteran",
            "disability_status": attrs.get("disability_status", "None") == "Yes",
            "employment_status": attrs.get("employment_type", ""),
            "profession": attrs.get("profession", ""),
            "marital_status": attrs.get("marital_status", ""),
            "income_bracket": attrs.get("income_bracket", ""),
            "mastery_scores": mastery_map,
            "conversation_history": history,
            "historical_document_paths": historical_document_paths,
            "is_new_user": not user.onboarded,
            "conversation_summary": conversation.conversation_summary if conversation else None,
            "needs_summarization": needs_summarization,
            "messages_to_summarize": messages_to_summarize,
            "cutoff_message_id": cutoff_message_id,
        }
    }