import logging
from datetime import datetime, timezone

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status


from ai_client import ai_client, AIServiceError
from apps.documents.models import UserDocument
from apps.documents.services import CloudStorageService
from apps.users.models import UserProfile
from bson import ObjectId
from bson.errors import InvalidId

from .chat_naming import format_auto_chat_name
from .masterPipeline import preprocess_query
from .models import Conversation, Message, TopicMastery, GeneratedDocument

from apps.mongo_db_config import get_knowledge_base_collection, get_self_assessments_collection
from datetime import datetime
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

ALLOWED_FILE_TYPES = {"application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per file


# ── Helpers ────────────────────────────────────────────────────────────────

def _validate_file(file) -> str | None:
    if file.content_type not in ALLOWED_FILE_TYPES:
        return f"'{file.name}' is not a PDF. Only PDF files are accepted."
    if file.size > MAX_FILE_SIZE_BYTES:
        return f"'{file.name}' exceeds the 10MB size limit."
    return None


def _format_structured_report(evaluation_report: list) -> str:
    lines = []
    for dim_report in evaluation_report:
        dim = dim_report.get("dimension", "")
        aspects = dim_report.get("aspects", [])
        all_labels = []
        for aspect in aspects:
            all_labels.extend(aspect.get("labels", []))
        gap = dim_report.get("most_critical_gap", "")
        lines.append(f"{dim}: [{', '.join(all_labels)}] — most critical gap: {gap}")
    return "\n".join(lines)


def _build_self_assessment_context(conversation) -> dict:
    base = {
        "legal_domain": conversation.legal_domain or "",
        "jurisdiction": conversation.jurisdiction or "",
        "legal_situation": conversation.legal_situation or "",
        "prior_experience": conversation.prior_experience or "",
        "desired_outcome": conversation.desired_outcome or "",
        "baseline_familiarity": conversation.baseline_familiarity or "",
    }
    if conversation.self_assessment_status != "completed":
        return base
    try:
        sa_col = get_self_assessments_collection()
        sa_doc = sa_col.find_one({"chat_id": str(conversation.id)})
        if not sa_doc:
            return base
        priority = sa_doc.get("priority", {})
        top_dim = priority.get("top_dimension", "")
        top_label = priority.get("top_label_in_top_dimension", "")
        priority_focus = f"{top_dim} – {top_label}" if top_dim and top_label else ""
        evaluation_report = sa_doc.get("evaluation_report", [])
        return {
            **base,
            "priority_focus": priority_focus,
            "evaluation_report": _format_structured_report(evaluation_report),
        }
    except Exception as e:
        logger.error(f"Failed to fetch self-assessment context for chat {conversation.id}: {e}")
        return base


def _upload_and_save_document(file, user, user_id) -> dict:
    storage_path = CloudStorageService.upload_document(
        user_id=str(user_id),
        user_name=f"{user.first_name}-{user.last_name}".lower(),
        file_obj=file,
    )

    doc = UserDocument.objects.create(
        user=user,
        file_name=file.name,
        storage_path=storage_path,
        file_size=file.size,
        status="uploaded",
    )

    return {
        "document_id": str(doc.id),
        "file_name": doc.file_name,
        "storage_path": doc.storage_path,
        "status": doc.status,
    }


# ── Views ──────────────────────────────────────────────────────────────────

def _list_user_chats(request, user_id):
    """GET /chats/:user_id/ — list all chat sessions for the user, sorted by updated_at desc."""
    if not ObjectId.is_valid(user_id):
        return Response(
            {"status": "error", "message": "Invalid user id"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
    except (UserProfile.DoesNotExist, InvalidId):
        return Response(
            {"status": "error", "message": "User does not exist"},
            status=status.HTTP_404_NOT_FOUND,
        )
    conversations = (
        Conversation.objects.filter(user=user).order_by("-updated_at")
    )
    chats = [
        {
            "chat_id": str(c.id),
            "chat_name": c.chat_name,
            "mode": c.mode,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conversations
    ]
    return Response(
        {
            "status": "success",
            "data": {
                "user_id": str(user_id),
                "chats": chats,
            },
        },
        status=status.HTTP_200_OK,
    )


def _get_user_and_conversation(user_id: str, chat_id: str):
    """
    Helper to fetch a user and one of their conversations with robust error handling.
    Used by endpoints that operate on a specific chat (rename, delete, etc.).
    """
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        return None, None, Response(
            {"status": "error", "message": "Invalid user_id or chat_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
    except (UserProfile.DoesNotExist, InvalidId):
        return None, None, Response(
            {"status": "error", "message": "User does not exist"},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        conversation = Conversation.objects.get(id=ObjectId(chat_id), user=user)
    except Conversation.DoesNotExist:
        return user, None, Response(
            {"status": "error", "message": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return user, conversation, None


@api_view(["GET", "PATCH", "DELETE"])
def chat_detail(request, user_id: str, chat_id: str):
    """
    GET: retrieve chat session details (same behavior as get_chat_session).
    PATCH: rename an existing chat (chat_name).
    DELETE: delete an existing chat and its messages.
    """
    if request.method == "GET":
        return get_chat_session(request, user_id, chat_id)

    user, conversation, error_response = _get_user_and_conversation(user_id, chat_id)
    if error_response is not None:
        return error_response

    if request.method == "PATCH":
        chat_name = (request.data.get("chat_name") or "").strip()
        if not chat_name:
            return Response(
                {"status": "error", "message": "Chat name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conversation.chat_name = chat_name
        conversation.save(update_fields=["chat_name", "updated_at"])
        return Response(
            {
                "status": "success",
                "data": {
                    "user_id": str(user.id),
                    "chat_id": str(conversation.id),
                    "chat_name": conversation.chat_name,
                    "created_at": conversation.created_at.isoformat(),
                    "updated_at": conversation.updated_at.isoformat(),
                },
            },
            status=status.HTTP_200_OK,
        )

    # DELETE
    conversation.delete()
    return Response(
        {
            "status": "success",
            "data": {
                "user_id": str(user.id),
                "chat_id": str(chat_id),
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
def chat_session(request, user_id):
    if request.method == "GET":
        return _list_user_chats(request, user_id)

    # Validate user
    try:
        if not ObjectId.is_valid(user_id):
            return Response(
                {"status": "error", "message": "Invalid user id"},
                status=400,
            )
        user = UserProfile.objects.get(id=user_id)
    except (UserProfile.DoesNotExist, InvalidId):
        return Response(
            {"status": "error", "message": "User does not exist"},
            status=404,
        )
    # Validate input fields
    legal_situation = request.data.get("legal_situation", "").strip()
    jurisdiction = request.data.get("jurisdiction", "").strip()
    prior_experience = request.data.get("prior_experience", "").strip()
    desired_outcome = request.data.get("desired_outcome", "").strip()
    if not legal_situation:
        return Response(
            {"status": "error", "message": "legal_situation is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not jurisdiction:
        return Response(
            {"status": "error", "message": "jurisdiction is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not prior_experience:
        return Response(
            {"status": "error", "message": "prior_experience is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not desired_outcome:
        return Response(
            {"status": "error", "message": "desired_outcome is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Retrieve Knowledge Base
    try:
        kb_result = ai_client.generate_kb(
            legal_situation=legal_situation,
            prior_experience=prior_experience,
            desired_outcome=desired_outcome,
            jurisdiction=jurisdiction,
        )
    except AIServiceError as e:
        logger.error(f"AI service error during KB generation for user {user_id}: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    # Store Conversation to Django ORM
    chat_name = format_auto_chat_name(
        kb_result.get("legal_domain"),
        legal_situation,
    )
    conversation = Conversation.objects.create(
        user=user,
        chat_name=chat_name,
        legal_situation=legal_situation,
        prior_experience=prior_experience,
        desired_outcome=desired_outcome,
        legal_domain=kb_result.get("legal_domain"),
        branch=kb_result.get("branch"),
        jurisdiction=kb_result.get("jurisdiction"),
        baseline_familiarity=kb_result.get("baseline_familiarity"),
        primary_intent=kb_result.get("primary_intent"),
        self_assessment_status="pending",
        example_text=kb_result.get("example_text"),
        empty_template=kb_result.get("empty_template"),
    )
    # Store Knowledge Base to PyMongo
    try:

        kb_col = get_knowledge_base_collection()
        kb_col.replace_one(
            {
                "legal_domain": kb_result.get("legal_domain"),
                "jurisdiction": kb_result.get("jurisdiction"),
            },
            {
                "legal_domain": kb_result.get("legal_domain"),
                "jurisdiction": kb_result.get("jurisdiction"),
                "title": kb_result.get("kb_title"),
                "content": {
                    "global_highlights": kb_result.get("global_highlights", []),
                    "rag_snippets": kb_result.get("rag_snippets", []),
                    "few_shot_examples": kb_result.get("few_shot_examples", {}),
                },
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )
    except Exception as e:
        logger.error(f"Failed to persist KB to MongoDB for user {user_id}: {e}")
    return Response(
        {
            "status": "success",
            "data": {
                "chat_id": str(conversation.id),
                "chat_name": conversation.chat_name,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "user_inputs": {
                    "legal_situation": conversation.legal_situation,
                    "prior_experience": conversation.prior_experience,
                    "desired_outcome": conversation.desired_outcome,
                    "jurisdiction": conversation.jurisdiction,
                },
                "self_assessment_data": {
                    "legal_domain": conversation.legal_domain,
                    "branch": conversation.branch,
                    "baseline_familiarity": conversation.baseline_familiarity,
                    "primary_intent": conversation.primary_intent,
                    "self_assessment_status": "pending",
                    "global_highlights": kb_result.get("global_highlights", []),
                    "example_text": conversation.example_text or "",
                    "empty_template": conversation.empty_template or "",
                }

            },
        },
        status=status.HTTP_201_CREATED,
    )

@api_view(["POST"])
def document_chat_session(request, user_id):
    """POST /chats/:user_id/documents/ — create a new document generation chat."""
    try:
        if not ObjectId.is_valid(user_id):
            return Response({"status": "error", "message": "Invalid user id"}, status=400)
        user = UserProfile.objects.get(id=user_id)
    except (UserProfile.DoesNotExist, InvalidId):
        return Response({"status": "error", "message": "User does not exist"}, status=404)

    document_type = request.data.get("document_type", "").strip()
    jurisdiction = request.data.get("jurisdiction", "").strip()

    if not document_type:
        return Response({"status": "error", "message": "document_type is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not jurisdiction:
        return Response({"status": "error", "message": "jurisdiction is required"}, status=status.HTTP_400_BAD_REQUEST)

    chat_name = f"{document_type} — {jurisdiction}"
    conversation = Conversation.objects.create(
        user=user,
        chat_name=chat_name,
        jurisdiction=jurisdiction,
        legal_domain=document_type,
        mode="document",
        self_assessment_status="skipped",
    )

    return Response(
        {
            "status": "success",
            "data": {
                "chat_id": str(conversation.id),
                "chat_name": conversation.chat_name,
                "mode": conversation.mode,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            },
        },
        status=status.HTTP_201_CREATED,
    )


# Internal helper only (no direct URL route). Must NOT be @api_view-decorated:
# chat_detail() calls it with an already-wrapped DRF Request, and a second
# @api_view wrap raises "request must be an HttpRequest, not rest_framework Request".
def get_chat_session(request, user_id, chat_id):
    try:
        # Validate User
        if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
            return Response(
                {"status": "error", "message": "Invalid user_id or chat_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validate chat id
        conversation = Conversation.objects.get(
            id=ObjectId(chat_id),
            user__id=ObjectId(user_id)
        )
    except Conversation.DoesNotExist:
        return Response(
            {"status": "error", "message": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    # Retrieve Knowledge Base from PyMongo
    kb_result = {
        "kb_title": "",
        "global_highlights": [],
        "few_shot_examples": {},
        "rag_snippets": [],
    }
    try:
        kb_col = get_knowledge_base_collection()
        kb_entry = kb_col.find_one({
            "legal_domain": conversation.legal_domain,
            "jurisdiction": conversation.jurisdiction,
        })
        if kb_entry:
            content = kb_entry.get("content", {})
            kb_result = {
                "kb_title": kb_entry.get("title", ""),
                "global_highlights": content.get("global_highlights", []),
                "few_shot_examples": content.get("few_shot_examples", {}),
                "rag_snippets": content.get("rag_snippets", []),
            }
    except Exception as e:
        logger.error(f"Failed to fetch KB for chat {chat_id}: {e}")
    return Response(
        {
            "status": "success",
            "data": {
                "chat_id": str(conversation.id),
                "chat_name": conversation.chat_name,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "user_inputs": {
                    "legal_situation": conversation.legal_situation,
                    "prior_experience": conversation.prior_experience,
                    "desired_outcome": conversation.desired_outcome,
                    "jurisdiction": conversation.jurisdiction,
                },
                "self_assessment_data": {
                    "legal_domain": conversation.legal_domain,
                    "branch": conversation.branch,
                    "baseline_familiarity": conversation.baseline_familiarity,
                    "primary_intent": conversation.primary_intent,
                    "self_assessment_status": conversation.self_assessment_status,
                    "global_highlights": kb_result.get("global_highlights", []),
                    "example_text": conversation.example_text,
                    "empty_template": conversation.empty_template,
                }

            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def chat_messages(request, user_id, chat_id):
    if request.method == "POST":
        return send_message(request, user_id, chat_id)
    return get_chat_messages(request, user_id, chat_id)


def send_message(request, user_id: str, chat_id: str):
    query = request.data.get("query", "").strip()
    files = request.FILES.getlist("documents")

    if not query:
        return Response(
            {"status": "error", "message": "query is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = UserProfile.objects.get(id=ObjectId(str(user_id)))
    except Exception:
        return Response(
            {"status": "error", "message": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        conversation = Conversation.objects.get(id=ObjectId(str(chat_id)))
    except Exception:
        return Response(
            {"status": "error", "message": "Conversation not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    for file in files:
        error = _validate_file(file)
        if error:
            return Response(
                {"status": "error", "message": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

    uploaded_documents = []
    storage_paths = []

    for file in files:
        try:
            doc_info = _upload_and_save_document(file, user, user_id)
            uploaded_documents.append({
                "document_id": doc_info["document_id"],
                "file_name": doc_info["file_name"],
                "status": doc_info["status"],
            })
            storage_paths.append(doc_info["storage_path"])
            logger.info(f"Uploaded: {doc_info['file_name']} → {doc_info['storage_path']}")
        except Exception as e:
            logger.error(f"Upload failed for {file.name}: {e}")
            return Response(
                {"status": "error", "message": f"Failed to upload '{file.name}': {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    preprocessed = preprocess_query(
        user_id=str(user_id),
        conversation_id=str(chat_id),
        user_query=query,
    )

    if not preprocessed["success"]:
        logger.error(f"Preprocessing failed: {preprocessed['error']}")
        return Response(
            {"status": "error", "message": preprocessed["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cleaned_query = preprocessed["data"]["cleaned_query"]
    user_context = preprocessed["data"]["user_context"]
    conversation_history = user_context["conversation_history"]
    needs_summarization = user_context.pop("needs_summarization", False)
    messages_to_summarize = user_context.pop("messages_to_summarize", [])
    cutoff_message_id = user_context.pop("cutoff_message_id", None)
    conversation_summary = user_context.pop("conversation_summary", None)
    logger.info("Preprocessing complete.")

    query_created_time = datetime.now(timezone.utc)
    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=query,
        document_paths=storage_paths,
    )
    for doc_info in uploaded_documents:
        UserDocument.objects.filter(id=ObjectId(doc_info["document_id"])).update(message_id=user_message.id)
    logger.info(f"Saved user message id={user_message.id}")

    # Merge current upload paths with document paths from previous messages in this chat
    historical_paths = preprocessed["data"]["user_context"].get("historical_document_paths", [])
    all_document_paths = storage_paths + [p for p in historical_paths if p not in storage_paths]
    logger.info(f"Document paths for this query: {all_document_paths}")

    self_assessment_context = _build_self_assessment_context(conversation)

    try:
        ai_result = ai_client.query(
            user_id=str(user_id),
            chat_id=str(chat_id),
            query=cleaned_query,
            document_paths=all_document_paths,
            conversation_history=conversation_history,
            user_context=preprocessed["data"]["user_context"],
            primary_topic=conversation.primary_topic,
            self_assessment_context=self_assessment_context,
            conversation_summary=conversation_summary,
            mode=conversation.mode,
            document_context={
                "document_type": conversation.legal_domain or "",
                "jurisdiction": conversation.jurisdiction or "",
            },
        )
        answer = ai_result["answer"]
        logger.info(f"[ANSWER PREVIEW] {answer[:200]}")
        logger.info("AI service responded successfully.")

    except AIServiceError as e:
        logger.error(f"AI service error: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    response_created_time = datetime.now(timezone.utc)
    llm_message = Message.objects.create(
        conversation=conversation,
        role="llm",
        content=answer,
    )
    logger.info(f"Saved LLM message id={llm_message.id}")

    if needs_summarization and messages_to_summarize and cutoff_message_id:
        from apps.chat.tasks import run_summarization_task
        run_summarization_task.delay(
            chat_id=str(conversation.id),
            messages_to_summarize=messages_to_summarize,
            existing_summary=conversation_summary,
            cutoff_message_id=str(cutoff_message_id),
        )
        logger.info(f"[SUMMARIZATION] Enqueued summarization task for chat {chat_id}")

    detected_topics = ai_result.get("detected_topic") or []
    confidence_delta = ai_result.get("confidence_delta")

    if detected_topics and confidence_delta is not None:
        for topic in detected_topics:
            try:
                mastery, created = TopicMastery.objects.get_or_create(
                    user=user,
                    topic=topic,
                    defaults={"mastery_level": 0.1},
                )
                current_score = mastery.mastery_level
                new_score = round(min(1.0, current_score * 0.8 + confidence_delta * 0.2), 4)
                mastery.mastery_level = new_score
                mastery.save()
                logger.info(f"Mastery updated: {topic} → {new_score} (was {current_score})")
            except Exception as e:
                logger.error(f"Mastery update failed for {topic}: {e}")

    if ai_result.get("document_context") and conversation.mode == "document":
        conversation.document_context = ai_result.get("document_context")
        conversation.save(update_fields=["document_context", "updated_at"])

    if detected_topics and not conversation.primary_topic:
        conversation.primary_topic = detected_topics[0]
        conversation.save()
        logger.info(f"Primary topic set: {detected_topics[0]}")

    return Response(
        {
            "status": "success",
            "data": {
                "user_id": str(user_id),
                "chat_id": str(chat_id),
                "chat_message_id": str(llm_message.id),
                "updated_at": response_created_time.isoformat(),
                "query": query,
                "response": answer,
                "document_urls": ai_result.get("document_urls", []),
                "documents": uploaded_documents,
                "query_created_time": query_created_time.isoformat(),
                "response_created_time": response_created_time.isoformat(),
                "ready_to_generate": ai_result.get("ready_to_generate", False),
                "document_context": ai_result.get("document_context", {}),
                "knowledge_sources": ai_result.get("knowledge_sources", []),
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def submit_self_assessment(request, user_id, chat_id):
    """
    POST /chats/<user_id>/<chat_id>/self-assessment/submit/
    Accepts the user's four-dimension form submission, calls the AI evaluate
    endpoint, persists the result to PyMongo self_assessments collection,
    and sets Conversation.self_assessment_status to 'completed'.
    """
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        return Response(
            {"status": "error", "message": "Invalid user_id or chat_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        conversation = Conversation.objects.get(
            id=ObjectId(chat_id),
            user__id=ObjectId(user_id),
        )
    except Conversation.DoesNotExist:
        return Response(
            {"status": "error", "message": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if conversation.self_assessment_status == "completed":
        return Response(
            {"status": "error", "message": "Self-assessment already completed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate required dimension inputs
    facts = request.data.get("facts")
    strategies = request.data.get("strategies")
    procedures = request.data.get("procedures")
    rationales = request.data.get("rationales")

    if not all([facts, strategies, procedures, rationales]):
        return Response(
            {"status": "error", "message": "facts, strategies, procedures, and rationales are all required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    for dim_name, dim_val in [("facts", facts), ("strategies", strategies), ("procedures", procedures),
                              ("rationales", rationales)]:
        if not isinstance(dim_val, dict) or "examples" not in dim_val or "uncertainties" not in dim_val:
            return Response(
                {"status": "error", "message": f"{dim_name} must have 'examples' and 'uncertainties' fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch KB from MongoDB — Django owns all DB access
    kb_content = {}
    try:
        kb_col = get_knowledge_base_collection()
        kb_entry = kb_col.find_one({
            "legal_domain": conversation.legal_domain,
            "jurisdiction": conversation.jurisdiction,
        })
        if kb_entry:
            kb_content = kb_entry.get("content", {})
        else:
            logger.warning(
                f"No KB found for domain={conversation.legal_domain} jurisdiction={conversation.jurisdiction}, proceeding with empty KB")
    except Exception as e:
        logger.error(f"KB fetch failed for chat {chat_id}: {e}")

    # Call AI evaluate endpoint — pass KB content directly
    try:
        eval_result = ai_client.evaluate_self_assessment(
            chat_id=str(chat_id),
            legal_situation=conversation.legal_situation or "",
            legal_domain=conversation.legal_domain or "",
            branch=conversation.branch or "",
            jurisdiction=conversation.jurisdiction or "",
            baseline_familiarity=conversation.baseline_familiarity or "low",
            primary_intent=conversation.primary_intent or "understand_options",
            prior_experience=conversation.prior_experience or "",
            desired_outcome=conversation.desired_outcome or "",
            kb_content=kb_content,
            facts=facts,
            strategies=strategies,
            procedures=procedures,
            rationales=rationales,
        )
    except AIServiceError as e:
        logger.error(f"AI evaluation failed for chat {chat_id}: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Persist to PyMongo self_assessments collection
    try:
        sa_col = get_self_assessments_collection()
        sa_col.replace_one(
            {"chat_id": str(chat_id)},
            {
                "chat_id": str(chat_id),
                "user_id": str(user_id),
                "legal_domain": conversation.legal_domain or "",
                "jurisdiction": conversation.jurisdiction or "",
                "student_text": eval_result.get("student_text", ""),
                "evaluation_report": eval_result.get("evaluation_report", []),
                "priority": eval_result.get("priority", {}),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )
    except Exception as e:
        logger.error(f"Failed to persist self-assessment for chat {chat_id}: {e}")

    # Update conversation status
    conversation.self_assessment_status = "completed"
    conversation.save()

    return Response(
        {
            "status": "success",
            "data": {
                "chat_id": str(chat_id),
                "self_assessment_status": "completed",
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def skip_self_assessment(request, user_id, chat_id):
    """
    POST /chats/<user_id>/<chat_id>/self-assessment/skip/
    Marks the self-assessment as skipped. The chat session (Step 3) will
    fall back to intake fields only when self_assessment_status is 'skipped'.
    """
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        return Response(
            {"status": "error", "message": "Invalid user_id or chat_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        conversation = Conversation.objects.get(
            id=ObjectId(chat_id),
            user__id=ObjectId(user_id),
        )
    except Conversation.DoesNotExist:
        return Response(
            {"status": "error", "message": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    conversation.self_assessment_status = "skipped"
    conversation.save()

    return Response(
        {
            "status": "success",
            "data": {
                "chat_id": str(chat_id),
                "self_assessment_status": "skipped",
            },
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
def ai_health(request):
    result = ai_client.health()
    http_status = (
        status.HTTP_200_OK
        if result.get("status") == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return Response(result, status=http_status)


def get_chat_messages(request, user_id, chat_id):
    try:
        if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
            return Response(
                {"status": "error", "message": "Invalid user_id or chat_id"},
                status=400)

        conversation = Conversation.objects.get(id=chat_id, user__id=user_id)

    except Conversation.DoesNotExist:
        return Response(
            {"status": "error", "message": "Chat not found"},
            status=404)

    messages = Message.objects.filter(conversation=conversation).order_by('created_at')

    chat_messages_list = []
    for message in messages:
        msg_data = {
            "chat_message_id": str(message.id),
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat()
        }
        if message.role == 'user':
            docs = UserDocument.objects.filter(message_id=message.id)
            msg_data["documents"] = [
                {"document_id": str(doc.id), "file_name": doc.file_name, "status": doc.status}
                for doc in docs
            ]
        chat_messages_list.append(msg_data)

    return Response({
        "status": "success",
        "data": {
            "user_id": user_id,
            "chat_id": chat_id,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "chat_messages": chat_messages_list
        }
    }, status=200)

@api_view(["POST"])
def generate_document(request, user_id, chat_id):
    """POST /chats/:user_id/:chat_id/generate-document/ — generate document and store it."""
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        return Response({"status": "error", "message": "Invalid user_id or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
        conversation = Conversation.objects.get(id=ObjectId(chat_id), user=user)
    except Exception:
        return Response({"status": "error", "message": "Chat not found."}, status=status.HTTP_404_NOT_FOUND)

    document_context = request.data.get("document_context", {})

    try:
        # Use structured document_context saved on conversation if available
        # Fall back to raw messages if not
        saved_context = conversation.document_context or {}
        merged_context = {**saved_context, **document_context}

        messages = Message.objects.filter(conversation=conversation).order_by("created_at")
        raw_context = "\n".join(
            f"{m.role.upper()}: {m.content}"
            for m in messages
        )

        doc_result = ai_client.generate_document_content(
            document_type=merged_context.get("document_type", conversation.legal_domain or "Legal Document"),
            jurisdiction=merged_context.get("jurisdiction", conversation.jurisdiction or ""),
            parties=merged_context.get("parties", ""),
            document_purpose=merged_context.get("document_purpose", ""),
            clauses=merged_context.get("clauses", []),
            special_provisions=merged_context.get("special_provisions", []),
            conversation_summary=None,
            full_context=raw_context,
        )
    except AIServiceError as e:
        logger.error(f"Document generation failed for chat {chat_id}: {e}")
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        pdf_bytes = ai_client.generate_document_pdf(
            document_type=merged_context.get("document_type", conversation.legal_domain or "Legal Document"),
            jurisdiction=merged_context.get("jurisdiction", conversation.jurisdiction or ""),
            parties=merged_context.get("parties", ""),
            document_purpose=merged_context.get("document_purpose", ""),
            clauses=merged_context.get("clauses", []),
            special_provisions=merged_context.get("special_provisions", []),
            conversation_summary=raw_context,
        )
        import io
        pdf_file_obj = io.BytesIO(pdf_bytes)
        pdf_file_obj.name = f"{doc_result.get('title', 'document').replace(' ', '_')}.pdf"
        storage_path = CloudStorageService.upload_document(
            user_id=str(user_id),
            user_name=f"{user.first_name}-{user.last_name}".lower(),
            file_obj=pdf_file_obj,
        )
    except Exception as e:
        logger.error(f"PDF upload failed for chat {chat_id}: {e}")
        storage_path = None

    version = GeneratedDocument.objects.filter(conversation=conversation).count() + 1
    generated_doc = GeneratedDocument.objects.create(
        conversation=conversation,
        user=user,
        document_type=doc_result.get("document_type", ""),
        title=doc_result.get("title", ""),
        content_markdown=doc_result.get("content_markdown", ""),
        storage_path=storage_path,
        version=version,
        context_summary=conversation.conversation_summary or "",
    )

    return Response(
        {
            "status": "success",
            "data": {
                "document_id": str(generated_doc.id),
                "title": generated_doc.title,
                "document_type": generated_doc.document_type,
                "version": generated_doc.version,
                "content_markdown": generated_doc.content_markdown,
                "storage_path": generated_doc.storage_path,
                "created_at": generated_doc.created_at.isoformat(),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def get_documents(request, user_id, chat_id):
    """GET /chats/:user_id/:chat_id/documents/ — list all generated documents for a chat."""
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        return Response({"status": "error", "message": "Invalid user_id or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
        conversation = Conversation.objects.get(id=ObjectId(chat_id), user=user)
    except Exception:
        return Response({"status": "error", "message": "Chat not found."}, status=status.HTTP_404_NOT_FOUND)

    documents = GeneratedDocument.objects.filter(conversation=conversation).order_by("-created_at")

    return Response(
        {
            "status": "success",
            "data": [
                {
                    "document_id": str(d.id),
                    "title": d.title,
                    "document_type": d.document_type,
                    "version": d.version,
                    "content_markdown": d.content_markdown,
                    "storage_path": d.storage_path,
                    "created_at": d.created_at.isoformat(),
                }
                for d in documents
            ],
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
def download_document(request, user_id, chat_id, document_id):
    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
        doc = GeneratedDocument.objects.get(id=ObjectId(document_id), user=user)
    except Exception:
        return Response({"status": "error", "message": "Document not found."}, status=404)

    # If we have a stored S3 path, serve from there directly
    if doc.storage_path:
        try:
            from apps.documents.services import CloudStorageService
            presigned_url = CloudStorageService.get_presigned_url(doc.storage_path)
            from django.http import HttpResponseRedirect
            import time
            return HttpResponseRedirect(f"{presigned_url}&t={int(time.time())}")
        except Exception as e:
            logger.warning(f"S3 fetch failed for document {document_id}, falling back to regeneration: {e}")

    # Fallback — regenerate PDF from raw messages
    try:
        messages = Message.objects.filter(conversation=doc.conversation).order_by("created_at")
        raw_context = "\n".join(
            f"{m.role.upper()}: {m.content}"
            for m in messages
        )
        pdf_bytes = ai_client.generate_document_pdf(
            document_type=doc.document_type,
            jurisdiction=doc.conversation.jurisdiction or "",
            parties="",
            document_purpose="",
            clauses=[],
            special_provisions=[],
            conversation_summary=raw_context,
        )
        from django.http import HttpResponse
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{doc.title.replace(" ", "_")}.pdf"'
        return response
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(["PATCH"])
def update_document(request, user_id, chat_id, document_id):
    try:
        user = UserProfile.objects.get(id=ObjectId(user_id))
        doc = GeneratedDocument.objects.get(id=ObjectId(document_id), user=user)
    except Exception:
        return Response({"status": "error", "message": "Document not found."}, status=404)

    content_markdown = request.data.get("content_markdown", "").strip()
    if not content_markdown:
        return Response({"status": "error", "message": "content_markdown is required."}, status=400)

    doc.content_markdown = content_markdown
    doc.save(update_fields=["content_markdown", "updated_at"])

    # Regenerate PDF from updated markdown and re-upload to S3
    try:
        pdf_bytes = ai_client.markdown_to_pdf(
            title=doc.title,
            content_markdown=content_markdown,
        )
        import io
        pdf_file_obj = io.BytesIO(pdf_bytes)
        pdf_file_obj.name = f"{doc.title.replace(' ', '_')}.pdf"
        storage_path = CloudStorageService.upload_document(
            user_id=str(user_id),
            user_name=f"{user.first_name}-{user.last_name}".lower(),
            file_obj=pdf_file_obj,
            existing_path=doc.storage_path,
        )
        logger.info(f"[UPDATE_DOCUMENT] Old storage_path: {doc.storage_path}")
        doc.storage_path = storage_path
        doc.save(update_fields=["storage_path", "updated_at"])
        logger.info(f"[UPDATE_DOCUMENT] New storage_path: {storage_path}")
    except Exception as e:
        logger.error(f"PDF regeneration failed after edit for document {document_id}: {e}")

    return Response({
        "status": "success",
        "data": {
            "document_id": str(doc.id),
            "content_markdown": doc.content_markdown,
        }
    }, status=200)

@api_view(["GET"])
def export_chat(request, user_id, chat_id):
    try:
        conversation = Conversation.objects.get(id=chat_id, user__id=user_id)
    except Conversation.DoesNotExist:
        return Response({"status": "error", "message": "Chat not found"}, status=404)

    messages = conversation.messages.order_by("created_at")

    lines = []
    lines.append(f"Chat Export: {conversation.title or 'Untitled'}")
    lines.append(f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 60)
    lines.append("")

    for msg in messages:
        role = "You" if msg.role == "user" else "METY"
        lines.append(f"[{role}]")
        lines.append(msg.content)
        lines.append("")

    content = "\n".join(lines)

    response = HttpResponse(content, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="chat-{chat_id}.txt"'
    return response