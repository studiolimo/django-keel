import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_complete_profile_requires_auth():
    client = APIClient()
    url = reverse("users:user-complete-profile")
    resp = client.patch(url, {}, content_type="application/json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_complete_profile_with_avatar_preset():
    client = APIClient()
    user = baker.make("users.User", profile_complete=False)
    client.force_authenticate(user=user)

    url = reverse("users:user-complete-profile")
    resp = client.patch(
        url,
        {
            "first_name": "Mario",
            "last_name": "Rossi",
            "avatar_preset": "preset_1",
        },
        content_type="application/json",
    )

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Mario"
    assert user.last_name == "Rossi"
    assert user.avatar_preset == "preset_1"
    assert user.profile_complete is True
    assert resp.json()["profile_complete"] is True


@pytest.mark.django_db
def test_complete_profile_missing_required_fields():
    client = APIClient()
    user = baker.make("users.User", profile_complete=False)
    client.force_authenticate(user=user)

    url = reverse("users:user-complete-profile")
    resp = client.patch(url, {"avatar_preset": "preset_1"}, content_type="application/json")

    assert resp.status_code == 400


@pytest.mark.django_db
def test_complete_profile_missing_avatar_fails():
    client = APIClient()
    user = baker.make("users.User", profile_complete=False)
    client.force_authenticate(user=user)

    url = reverse("users:user-complete-profile")
    resp = client.patch(
        url, {"first_name": "Mario", "last_name": "Rossi"}, content_type="application/json"
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_delete_account_requires_auth():
    client = APIClient()
    url = reverse("users:user-delete-account")
    resp = client.delete(url)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_delete_account_removes_user():
    UserModel = get_user_model()
    client = APIClient()
    user = baker.make("users.User", email="todelete@example.com")
    client.force_authenticate(user=user)

    url = reverse("users:user-delete-account")
    resp = client.delete(url)

    assert resp.status_code == 204
    assert not UserModel.objects.filter(email="todelete@example.com").exists()
