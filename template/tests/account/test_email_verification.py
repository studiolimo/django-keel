from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from model_bakery import baker
from rest_framework.test import APIClient

from apps.account.social_auth import social_login
from apps.account.tasks import send_email_verification_task
from apps.account.tokens import email_verification_token


@pytest.mark.django_db
def test_register_sets_terms_accepted_implicitly(client):
    url = reverse("auth_register")
    resp = client.post(
        url,
        {
            "email": "new@example.com",
            "password": "Pass123!",
            "password2": "Pass123!",
        },
        content_type="application/json",
    )

    assert resp.status_code == 201
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    user = UserModel.objects.get(email="new@example.com")
    assert user.terms_accepted_at is not None
    assert user.email_verified is False


@pytest.mark.django_db
def test_register_triggers_verification_email(client):
    url = reverse("auth_register")
    with patch("apps.account.tasks.send_email_verification_task.delay") as mock_delay:
        client.post(
            url,
            {
                "email": "new2@example.com",
                "password": "Pass123!",
                "password2": "Pass123!",
            },
            content_type="application/json",
        )
        mock_delay.assert_called_once()


@pytest.mark.django_db
def test_login_returns_email_verified_and_profile_complete(client):
    user = baker.make(
        "users.User", email="test@example.com", email_verified=True, profile_complete=True
    )
    user.set_password("Pass123!")
    user.save()

    url = reverse("auth_login")
    resp = client.post(
        url, {"email": "test@example.com", "password": "Pass123!"}, content_type="application/json"
    )

    assert resp.status_code == 200
    assert "email_verified" in resp.json()
    assert "profile_complete" in resp.json()
    assert resp.json()["email_verified"] is True
    assert resp.json()["profile_complete"] is True


@pytest.mark.django_db
def test_email_verification_token_is_valid_before_verification():
    user = baker.make("users.User", email_verified=False)
    token = email_verification_token.make_token(user)
    assert email_verification_token.check_token(user, token) is True


@pytest.mark.django_db
def test_email_verification_token_is_invalid_after_verification():
    user = baker.make("users.User", email_verified=False)
    token = email_verification_token.make_token(user)
    # Simula verifica avvenuta
    user.email_verified = True
    user.save()
    assert email_verification_token.check_token(user, token) is False


@pytest.mark.django_db
def test_send_email_verification_task_skips_already_verified():
    user = baker.make("users.User", email_verified=True)
    with patch("apps.notifications.service.NotificationService.send_notification") as mock_send:
        send_email_verification_task(user.pk)
        mock_send.assert_not_called()


@pytest.mark.django_db
def test_send_email_verification_task_sends_for_unverified():
    user = baker.make("users.User", email_verified=False, first_name="Mario")
    with patch("apps.notifications.service.NotificationService.send_notification") as mock_send:
        send_email_verification_task(user.pk)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "verify_url" in call_kwargs["context"]


@pytest.mark.django_db
def test_verify_email_success(client):
    user = baker.make("users.User", email_verified=False)
    token = email_verification_token.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    url = reverse("verify-email")
    resp = client.post(url, {"uid": uidb64, "token": token}, content_type="application/json")

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is True
    assert user.email_verified_at is not None


@pytest.mark.django_db
def test_verify_email_invalid_token(client):
    user = baker.make("users.User", email_verified=False)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    url = reverse("verify-email")
    resp = client.post(
        url, {"uid": uidb64, "token": "invalid-token"}, content_type="application/json"
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_resend_verification_requires_email():
    client = APIClient()
    url = reverse("resend-verification")
    resp = client.post(url, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_resend_verification_skips_already_verified():
    user = baker.make("users.User", email_verified=True)
    client = APIClient()

    url = reverse("resend-verification")
    with patch("apps.account.tasks.send_email_verification_task.delay") as mock_delay:
        resp = client.post(url, {"email": user.email}, content_type="application/json")
        mock_delay.assert_not_called()

    assert resp.status_code == 200


@pytest.mark.django_db
def test_resend_verification_sends_for_unverified():
    user = baker.make("users.User", email_verified=False)
    api_client = APIClient()

    url = reverse("resend-verification")
    with patch("apps.account.tasks.send_email_verification_task.delay") as mock_delay:
        resp = api_client.post(url, {"email": user.email}, content_type="application/json")
        mock_delay.assert_called_once_with(user.pk)

    assert resp.status_code == 200


@pytest.mark.django_db
def test_resend_verification_unknown_email_returns_200():
    client = APIClient()
    url = reverse("resend-verification")
    with patch("apps.account.tasks.send_email_verification_task.delay") as mock_delay:
        resp = client.post(
            url, {"email": "nonexistent@example.com"}, content_type="application/json"
        )
        mock_delay.assert_not_called()
    assert resp.status_code == 200


@pytest.mark.django_db
def test_social_login_google_new_user_sets_email_verified():
    from apps.account.models import SocialProvider

    google_info = {
        "uid": "google-uid-123",
        "email": "google@example.com",
        "first_name": "Mario",
        "last_name": "Rossi",
        "extra_data": {"picture": "", "email_verified": True},
    }
    with (
        patch.dict(
            "apps.account.social_auth.PROVIDER_VERIFIERS",
            {SocialProvider.GOOGLE: lambda token: google_info},
        ),
        patch("apps.account.tasks.send_user_welcome_email_task.delay"),
        patch("apps.account.tasks.send_email_verification_task.delay") as mock_email,
    ):
        result = social_login("google", "fake-token")

    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(email="google@example.com")
    assert user.email_verified is True
    mock_email.assert_not_called()  # Google already verified, no email sent
    assert result["email_verified"] is True


@pytest.mark.django_db
def test_social_login_facebook_new_user_triggers_email_verification():
    from apps.account.models import SocialProvider

    fb_info = {
        "uid": "fb-uid-456",
        "email": "fb@example.com",
        "first_name": "Luigi",
        "last_name": "Bianchi",
        "extra_data": {"picture": ""},
    }
    with (
        patch.dict(
            "apps.account.social_auth.PROVIDER_VERIFIERS",
            {SocialProvider.FACEBOOK: lambda token: fb_info},
        ),
        patch("apps.account.tasks.send_user_welcome_email_task.delay"),
        patch("apps.account.tasks.send_email_verification_task.delay") as mock_email,
    ):
        result = social_login("facebook", "fake-token")

    assert result["email_verified"] is False
    mock_email.assert_called_once()
