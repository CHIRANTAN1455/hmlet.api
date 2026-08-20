"""Authentication and the secure-by-default posture."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_register_returns_user_and_tokens(api_client):
    response = api_client.post(
        "/api/auth/register",
        {"email": "new@example.com", "full_name": "New Staff", "password": "Str0ngPass!23"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user"]["email"] == "new@example.com"
    assert response.data["access"] and response.data["refresh"]
    assert "password" not in response.data["user"]


def test_registered_user_is_staff(api_client):
    api_client.post(
        "/api/auth/register",
        {"email": "new@example.com", "full_name": "New Staff", "password": "Str0ngPass!23"},
        format="json",
    )
    assert User.objects.get(email="new@example.com").is_staff is True


def test_password_is_hashed_not_stored_plainly(api_client):
    password = "Str0ngPass!23"
    api_client.post(
        "/api/auth/register",
        {"email": "new@example.com", "full_name": "New Staff", "password": password},
        format="json",
    )
    user = User.objects.get(email="new@example.com")
    assert user.password != password
    assert user.check_password(password)


@pytest.mark.parametrize("email", ["staff@example.com", "STAFF@example.com", "Staff@Example.com"])
def test_duplicate_email_is_rejected_regardless_of_case(api_client, staff_user, email):
    response = api_client.post(
        "/api/auth/register",
        {"email": email, "full_name": "Impostor", "password": "Str0ngPass!23"},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.data["error"]["details"]


@pytest.mark.parametrize("password", ["short", "12345678", "password"])
def test_weak_passwords_are_rejected(api_client, password):
    response = api_client.post(
        "/api/auth/register",
        {"email": "weak@example.com", "full_name": "Weak", "password": password},
        format="json",
    )
    assert response.status_code == 400


def test_login_returns_tokens_and_user(api_client, staff_user):
    response = api_client.post(
        "/api/auth/login",
        {"email": staff_user.email, "password": "TestPass123!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["user"]["email"] == staff_user.email
    assert response.data["access"]


def test_login_with_wrong_password_is_401(api_client, staff_user):
    response = api_client.post(
        "/api/auth/login",
        {"email": staff_user.email, "password": "nope"},
        format="json",
    )
    assert response.status_code == 401


def test_refresh_issues_a_new_access_token(api_client, staff_user):
    login = api_client.post(
        "/api/auth/login",
        {"email": staff_user.email, "password": "TestPass123!"},
        format="json",
    )
    response = api_client.post(
        "/api/auth/refresh", {"refresh": login.data["refresh"]}, format="json"
    )
    assert response.status_code == 200
    assert response.data["access"]


def test_me_returns_the_authenticated_user(auth_client, staff_user):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.data["email"] == staff_user.email


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/auth/me"),
        ("get", "/api/properties"),
        ("post", "/api/properties"),
        ("get", "/api/units"),
        ("get", "/api/members"),
        ("post", "/api/members"),
        ("get", "/api/contracts"),
        ("post", "/api/contracts"),
    ],
)
def test_every_protected_endpoint_requires_a_token(api_client, method, path):
    """Secure by default: DRF is configured to require auth unless a view opts out.

    Parametrised over the whole surface so a new endpoint that forgets to
    authenticate is caught here rather than in production.
    """
    response = getattr(api_client, method)(path)
    assert response.status_code == 401, f"{method.upper()} {path} was not protected"


def test_malformed_token_is_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not.a.real.token")
    assert api_client.get("/api/auth/me").status_code == 401


def test_errors_use_the_standard_envelope(api_client):
    response = api_client.get("/api/auth/me")
    assert set(response.data) == {"error"}
    assert {"code", "message"} <= set(response.data["error"])
