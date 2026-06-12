"""Pytest configuration and fixtures."""

from datetime import time, timedelta

import pytest
from django.test import Client
from rest_framework.test import APIClient

from apps.users.models import User

# Test constants
TEST_PASSWORD = "testpass123"


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user):
    """API client authenticated with a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """API client authenticated with an admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        email="test@example.com",
        password=TEST_PASSWORD,
        first_name="Test",
        last_name="User",
        is_active=True,
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(email="admin@example.com", password=TEST_PASSWORD)


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return User.objects.create_user(
        email="staff@example.com", password=TEST_PASSWORD, is_staff=True
    )


@pytest.fixture
def multiple_users(db):
    """Create multiple test users."""

    users = []
    for i in range(3):
        user = User.objects.create_user(
            email=f"user{i}@example.com",
            password=TEST_PASSWORD,
            first_name=f"User{i}",
            last_name="Test",
        )
        users.append(user)
    return users
