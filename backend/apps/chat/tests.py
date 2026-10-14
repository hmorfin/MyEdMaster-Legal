import pytest
from bson import ObjectId

from apps.chat.models import Conversation, Message
from apps.documents.models import UserDocument
from apps.users.models import UserProfile


def _messages_url(user_id: str, chat_id: str) -> str:
    return f"/api/v1/chats/{user_id}/{chat_id}/messages/"

def _chat_detail_url(user_id: str, chat_id: str) -> str:
    return f"/api/v1/chats/{user_id}/{chat_id}/"


@pytest.mark.django_db
def test_get_chat_messages_success_returns_messages_and_user_docs(client):
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )
    convo = Conversation.objects.create(user=user, chat_name="Test chat")

    user_msg = Message.objects.create(
        conversation=convo,
        role="user",
        content="hello",
    )
    llm_msg = Message.objects.create(
        conversation=convo,
        role="llm",
        content="hi there, how can I help you today?",
    )

    doc = UserDocument.objects.create(
        user=user,
        message=user_msg,
        file_name="contract.pdf",
        storage_path="s3://bucket/contract.pdf",
        file_size=123,
        status="uploaded",
    )

    response = client.get(_messages_url(str(user.id), str(convo.id)))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["user_id"] == str(user.id)
    assert payload["data"]["chat_id"] == str(convo.id)

    msgs = payload["data"]["chat_messages"]
    assert len(msgs) == 2

    assert msgs[0]["chat_message_id"] == str(user_msg.id)
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "hello"
    assert "created_at" in msgs[0]
    assert msgs[0]["documents"] == [
        {"document_id": str(doc.id), "file_name": "contract.pdf", "status": "uploaded"}
    ]

    assert msgs[1]["chat_message_id"] == str(llm_msg.id)
    assert msgs[1]["role"] == "llm"
    assert msgs[1]["content"] == "hi there, how can I help you today?"
    assert "created_at" in msgs[1]
    assert "documents" not in msgs[1]


@pytest.mark.django_db
def test_get_chat_messages_invalid_ids_returns_400(client):
    response = client.get(_messages_url("not-an-objectid", "also-bad"))
    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["message"] == "Invalid user_id or chat_id"


@pytest.mark.django_db
def test_get_chat_messages_chat_not_found_returns_404(client):
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )
    missing_chat_id = str(ObjectId())

    response = client.get(_messages_url(str(user.id), missing_chat_id))
    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["message"] == "Chat not found"


@pytest.mark.django_db
def test_rename_chat_success(client):
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )
    convo = Conversation.objects.create(user=user, chat_name="Old name")

    response = client.patch(
        _chat_detail_url(str(user.id), str(convo.id)),
        {"chat_name": "New name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["user_id"] == str(user.id)
    assert payload["data"]["chat_id"] == str(convo.id)
    assert payload["data"]["chat_name"] == "New name"
    assert "created_at" in payload["data"]
    assert "updated_at" in payload["data"]

    convo.refresh_from_db()
    assert convo.chat_name == "New name"


@pytest.mark.django_db
def test_chat_detail_invalid_ids_returns_400(client):
    response = client.patch(
        _chat_detail_url("not-an-objectid", "also-bad"),
        {"chat_name": "New name"},
        content_type="application/json",
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["message"] == "Invalid user_id or chat_id"


@pytest.mark.django_db
def test_rename_chat_not_found_returns_404(client):
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )
    missing_chat_id = str(ObjectId())

    response = client.patch(
        _chat_detail_url(str(user.id), missing_chat_id),
        {"chat_name": "New name"},
        content_type="application/json",
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["message"] == "Chat not found"


@pytest.mark.django_db
def test_delete_chat_success_deletes_conversation_and_messages(client):
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )
    convo = Conversation.objects.create(user=user, chat_name="To delete")
    Message.objects.create(conversation=convo, role="user", content="hello")
    Message.objects.create(conversation=convo, role="llm", content="hi")

    response = client.delete(_chat_detail_url(str(user.id), str(convo.id)))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["user_id"] == str(user.id)
    assert payload["data"]["chat_id"] == str(convo.id)

    assert Conversation.objects.filter(id=convo.id).count() == 0
    assert Message.objects.filter(conversation=convo).count() == 0

