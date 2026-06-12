"""Fixture per i test della dashboard staff.

staff_client/normal_user servono ai test delle view protette (permessi, liste,
form). admin_user e staff_user arrivano dal conftest root (tests/conftest.py).
"""

import pytest

from apps.users.models import User
from tests.conftest import TEST_PASSWORD


@pytest.fixture
def staff_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def normal_user(db):
    return User.objects.create_user(email="utente@example.com", password=TEST_PASSWORD)
