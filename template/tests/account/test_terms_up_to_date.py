import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils import timezone as tz
from model_bakery import baker


@pytest.mark.django_db
class TestTermsUpToDate:
    def test_no_documents_returns_true(self, user):
        """No LegalDocument in DB → no version required → True, but only if user has accepted."""
        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 1, 1, 12, 0, 0))
        user.save()
        assert user.terms_up_to_date is True

    def test_null_terms_accepted_at_returns_false(self, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        user.terms_accepted_at = None
        user.save()
        assert user.terms_up_to_date is False

    def test_accepted_before_document_returns_false(self, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 3, 1))
        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 2, 1, 12, 0, 0))
        user.save()
        assert user.terms_up_to_date is False

    def test_accepted_after_document_returns_true(self, user):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 2, 1, 12, 0, 0))
        user.save()
        assert user.terms_up_to_date is True

    def test_latest_document_wins_across_types(self, user):
        """Privacy Policy updated later than T&C — Privacy date is what matters."""
        baker.make(
            "account.LegalDocument",
            document_type="terms",
            effective_date=datetime.date(2026, 1, 1),
        )
        baker.make(
            "account.LegalDocument",
            document_type="privacy",
            effective_date=datetime.date(2026, 3, 1),
        )
        # Accepted after T&C but before Privacy Policy update
        user.terms_accepted_at = timezone.make_aware(datetime.datetime(2026, 2, 1, 12, 0, 0))
        user.save()
        assert user.terms_up_to_date is False


@pytest.mark.django_db
class TestLoginTermsUpToDateFlag:
    def test_login_returns_terms_up_to_date_false_when_user_never_accepted(self, client):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        User = get_user_model()
        User.objects.create_user(email="login@example.com", password="TestPass1!")
        # terms_accepted_at is null by default

        response = client.post(
            reverse("auth_login"),
            {"email": "login@example.com", "password": "TestPass1!"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is False

    def test_login_returns_terms_up_to_date_true_when_user_accepted(self, client):
        baker.make("account.LegalDocument", effective_date=datetime.date(2026, 1, 1))
        User = get_user_model()
        u = User.objects.create_user(email="login2@example.com", password="TestPass1!")
        u.terms_accepted_at = tz.make_aware(datetime.datetime(2026, 2, 1))
        u.save()

        response = client.post(
            reverse("auth_login"),
            {"email": "login2@example.com", "password": "TestPass1!"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["terms_up_to_date"] is True
