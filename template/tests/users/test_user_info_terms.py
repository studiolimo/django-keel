import datetime

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

INFO_URL = reverse("users:user-info")


@pytest.fixture
def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestUserInfoTermsUpToDate:
    def test_no_legal_documents_returns_true(self, authed_client, user):
        from django.utils import timezone

        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 1, 1, 12, 0, 0))
        user.save()
        response = authed_client.get(INFO_URL)
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is True

    def test_null_terms_accepted_at_returns_false(self, authed_client, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        user.terms_accepted_at = None
        user.save()

        response = authed_client.get(INFO_URL)
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is False

    def test_accepted_after_latest_document_returns_true(self, authed_client, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        from django.utils import timezone

        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 2, 1))
        user.save()

        response = authed_client.get(INFO_URL)
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is True

    def test_accepted_before_latest_document_returns_false(self, authed_client, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 3, 1))
        from django.utils import timezone

        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 2, 1))
        user.save()

        response = authed_client.get(INFO_URL)
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is False

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        response = client.get(INFO_URL)
        assert response.status_code == 401
