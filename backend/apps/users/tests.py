import pytest

from apps.users.models import UserProfile


LOGIN_URL = "/api/v1/users/login/"
CREATE_USER_URL = "/api/v1/users/"


def _modify_user_url(user_id: str) -> str:
    return f"/api/v1/users/{user_id}/"


@pytest.mark.django_db
def test_login_success_returns_user_profile(client):
    """Login with an existing email returns full user profile."""
    user = UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
        phone="1234567890",
        location={"city": "Phoenix"},
        user_attributes={"profession": "Engineer"},
        onboarded=True,
    )

    response = client.post(
        LOGIN_URL,
        {"email": "john.smith@example.com"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["id"] == str(user.id)
    assert data["data"]["first_name"] == "John"
    assert data["data"]["last_name"] == "Smith"
    assert data["data"]["email"] == "john.smith@example.com"
    assert data["data"]["onboarded"] is True


@pytest.mark.django_db
def test_login_is_case_insensitive(client):
    """Email lookup should be case insensitive."""
    UserProfile.objects.create(
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
    )

    response = client.post(
        LOGIN_URL,
        {"email": "JOHN.SMITH@EXAMPLE.COM"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["email"] == "john.smith@example.com"


@pytest.mark.django_db
def test_login_requires_email(client):
    """Missing email should return 400."""
    response = client.post(
        LOGIN_URL,
        {},
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "email is required"


@pytest.mark.django_db
def test_login_nonexistent_email_returns_404(client):
    """Unknown email should return 404"""
    response = client.post(
        LOGIN_URL,
        {"email": "does.not.exist@example.com"},
        content_type="application/json",
    )

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["message"] == "No user with this email."


@pytest.mark.django_db
def test_create_user_success(client):
    response = client.post(
        CREATE_USER_URL,
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice.johnson@example.com",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "success"
    assert "id" in payload["data"]
    assert payload["data"]["onboarded"] is False
    assert "createdAt" in payload["data"]

    assert UserProfile.objects.filter(email="alice.johnson@example.com").count() == 1


@pytest.mark.django_db
def test_modify_user_success_updates_profile_and_marks_onboarded(client):
    user = UserProfile.objects.create(
        first_name="Alice",
        last_name="Johnson",
        email="alice.johnson@example.com",
        onboarded=False,
    )

    response = client.put(
        _modify_user_url(str(user.id)),
        {
            "first_name": "Alicia",
            "last_name": "Jones",
            "phone": "5551234567",
            "dob": "1995-06-01",
            "location": {"city": "Tempe"},
            "user_attributes": {
                "profession": "IT Professional",
                "employment_type": "Full-Time",
                "veteran_status": "Non-Veteran",
                "disability_status": "None",
                "marital_status": "Single",
                "income_bracket": "$50,000 - $74,999",
            },
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["id"] == str(user.id)

    user.refresh_from_db()
    assert user.first_name == "Alicia"
    assert user.last_name == "Jones"
    assert user.phone == "5551234567"
    assert str(user.dob) == "1995-06-01"
    assert user.location == {"city": "Tempe"}
    assert user.user_attributes["profession"] == "IT Professional"
    assert user.onboarded is True


@pytest.mark.django_db
def test_modify_user_not_found_returns_404(client):
    response = client.put(
        _modify_user_url("507f1f77bcf86cd799439011"),
        {"first_name": "Nobody"},
        content_type="application/json",
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["message"] == "User does not exist"

