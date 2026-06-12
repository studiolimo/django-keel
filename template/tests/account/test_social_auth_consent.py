from unittest.mock import patch

import pytest

SOCIAL_URL = "/api/account/social-login/"

VALID_GOOGLE_PAYLOAD = {
    "provider": "google",
    "token": "fake-google-token",
    "terms_accepted": True,
}

MOCK_USER_INFO = {
    "uid": "google-uid-123",
    "email": "googleuser@example.com",
    "first_name": "Google",
    "last_name": "User",
    "extra_data": {"picture": "", "email_verified": True},
}


@pytest.mark.django_db
class TestSocialLoginConsent:
    def _mock_verify(self):
        from apps.account.models import SocialProvider

        return patch.dict(
            "apps.account.social_auth.PROVIDER_VERIFIERS",
            {SocialProvider.GOOGLE: lambda token: MOCK_USER_INFO},
        )

    def test_new_social_user_with_terms_accepted_succeeds(self, client):
        with self._mock_verify():
            response = client.post(
                SOCIAL_URL, VALID_GOOGLE_PAYLOAD, content_type="application/json"
            )
        assert response.status_code == 200
        assert response.json()["created"] is True

    def test_new_social_user_terms_accepted_at_is_set(self, client):
        from django.contrib.auth import get_user_model

        with self._mock_verify():
            client.post(SOCIAL_URL, VALID_GOOGLE_PAYLOAD, content_type="application/json")
        user = get_user_model().objects.get(email="googleuser@example.com")
        assert user.terms_accepted_at is not None

    def test_new_social_user_terms_accepted_implicit_regardless_of_flag(self, client):
        """T&C acceptance is implicit on social login — terms_accepted flag is ignored."""
        from django.contrib.auth import get_user_model

        payload = {**VALID_GOOGLE_PAYLOAD, "terms_accepted": False}
        with (
            self._mock_verify(),
            patch("apps.account.tasks.send_user_welcome_email_task.delay"),
            patch("apps.account.tasks.send_email_verification_task.delay"),
        ):
            response = client.post(SOCIAL_URL, payload, content_type="application/json")
        assert response.status_code == 200
        user = get_user_model().objects.get(email="googleuser@example.com")
        assert user.terms_accepted_at is not None

    def test_new_social_user_marketing_consent_saved(self, client):
        from django.contrib.auth import get_user_model

        payload = {**VALID_GOOGLE_PAYLOAD, "marketing_consent": True}
        with self._mock_verify():
            client.post(SOCIAL_URL, payload, content_type="application/json")
        user = get_user_model().objects.get(email="googleuser@example.com")
        assert user.marketing_consent is True
        assert user.marketing_consent_at is not None

    def test_existing_social_user_login_ignores_terms_fields(self, client):
        """Returning user — consent fields are ignored, no error even if False."""
        from django.contrib.auth import get_user_model

        from apps.account.models import SocialAccount

        User = get_user_model()
        existing_user = User.objects.create_user(email="googleuser@example.com", password=None)
        existing_user.set_unusable_password()
        existing_user.save()
        SocialAccount.objects.create(
            user=existing_user,
            provider="google",
            provider_uid="google-uid-123",
            extra_data={},
        )

        payload = {**VALID_GOOGLE_PAYLOAD, "terms_accepted": False}
        with self._mock_verify():
            response = client.post(SOCIAL_URL, payload, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["created"] is False

    def test_email_auto_link_ignores_terms_fields(self, client):
        """Case 2: user exists by email but no SocialAccount — auto-link, no consent validation."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        # User registered via email (no SocialAccount)
        User.objects.create_user(email="googleuser@example.com", password="TestPass1!")
        # No SocialAccount created — this triggers Case 2 (email auto-link)

        # terms_accepted=False should NOT cause a 400 for an existing user
        payload = {**VALID_GOOGLE_PAYLOAD, "terms_accepted": False}
        with self._mock_verify():
            response = client.post(SOCIAL_URL, payload, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["created"] is False
        assert "terms_up_to_date" in response.json()

    def test_social_login_returns_terms_up_to_date_flag(self, client):
        import datetime

        from model_bakery import baker

        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        with self._mock_verify():
            response = client.post(
                SOCIAL_URL, VALID_GOOGLE_PAYLOAD, content_type="application/json"
            )
        data = response.json()
        assert "terms_up_to_date" in data
