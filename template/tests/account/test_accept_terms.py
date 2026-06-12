import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

ACCEPT_URL = reverse("accept_terms")


@pytest.mark.django_db
class TestAcceptTermsView:
    def _auth_client(self, client, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = str(RefreshToken.for_user(user).access_token)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return client

    def test_authenticated_user_can_accept_terms(self, client, user):
        authed = self._auth_client(client, user)
        response = authed.post(ACCEPT_URL, {}, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is True

    def test_terms_accepted_at_is_updated(self, client, user):
        authed = self._auth_client(client, user)
        authed.post(ACCEPT_URL, {}, content_type="application/json")
        user.refresh_from_db()
        assert user.terms_accepted_at is not None

    def test_unauthenticated_request_returns_401(self, client):
        response = client.post(ACCEPT_URL, {}, content_type="application/json")
        assert response.status_code == 401

    def test_marketing_consent_true_updates_consent(self, client, user):
        authed = self._auth_client(client, user)
        authed.post(ACCEPT_URL, {"marketing_consent": True}, content_type="application/json")
        user.refresh_from_db()
        assert user.marketing_consent is True
        assert user.marketing_consent_at is not None

    def test_marketing_consent_false_withdraws_consent(self, client, user):
        user.marketing_consent = True
        user.marketing_consent_at = timezone.now()
        user.save()

        authed = self._auth_client(client, user)
        authed.post(ACCEPT_URL, {"marketing_consent": False}, content_type="application/json")
        user.refresh_from_db()
        assert user.marketing_consent is False
        # marketing_consent_at preserved (not cleared) for audit trail
        assert user.marketing_consent_at is not None

    def test_omitting_marketing_consent_preserves_existing_value(self, client, user):
        user.marketing_consent = True
        user.marketing_consent_at = timezone.now()
        user.save()

        authed = self._auth_client(client, user)
        authed.post(ACCEPT_URL, {}, content_type="application/json")
        user.refresh_from_db()
        assert user.marketing_consent is True

    def test_acceptance_with_legal_document_returns_terms_up_to_date_true(self, client, user):
        import datetime

        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        # user.terms_accepted_at is None — so terms_up_to_date is False before calling
        assert user.terms_up_to_date is False

        authed = self._auth_client(client, user)
        response = authed.post(ACCEPT_URL, {}, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is True
