import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

REGISTER_URL = reverse("auth_register")

VALID_PAYLOAD = {
    "email": "newuser@example.com",
    "first_name": "Mario",
    "last_name": "Rossi",
    "password": "SecurePass1!",
    "password2": "SecurePass1!",
}


@pytest.mark.django_db
class TestRegisterConsent:
    def test_registration_succeeds(self, client):
        response = client.post(REGISTER_URL, VALID_PAYLOAD, content_type="application/json")
        assert response.status_code == 201

    def test_terms_accepted_at_is_set_implicitly_on_registration(self, client):
        client.post(REGISTER_URL, VALID_PAYLOAD, content_type="application/json")
        user = get_user_model().objects.get(email="newuser@example.com")
        assert user.terms_accepted_at is not None

    def test_marketing_consent_true_sets_marketing_consent_at(self, client):
        payload = {**VALID_PAYLOAD, "marketing_consent": True}
        client.post(REGISTER_URL, payload, content_type="application/json")
        user = get_user_model().objects.get(email="newuser@example.com")
        assert user.marketing_consent is True
        assert user.marketing_consent_at is not None

    def test_marketing_consent_false_leaves_marketing_consent_at_null(self, client):
        payload = {**VALID_PAYLOAD, "marketing_consent": False}
        client.post(REGISTER_URL, payload, content_type="application/json")
        user = get_user_model().objects.get(email="newuser@example.com")
        assert user.marketing_consent is False
        assert user.marketing_consent_at is None

    def test_marketing_consent_defaults_to_false(self, client):
        client.post(REGISTER_URL, VALID_PAYLOAD, content_type="application/json")
        user = get_user_model().objects.get(email="newuser@example.com")
        assert user.marketing_consent is False
