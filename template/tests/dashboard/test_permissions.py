import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_anonimo_rediretto_al_login_admin(client):
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302
    # L'admin è sotto i18n_patterns, quindi l'URL ha il prefisso lingua (es. /it/admin/login/).
    assert "/admin/login/" in response.url


@pytest.mark.django_db
def test_utente_normale_non_accede(client, normal_user):
    client.force_login(normal_user)
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_staff_non_superuser_non_accede_a_view_superuser(client, staff_user):
    # L'index è protetto da SuperuserPermissionMixin: staff puro → redirect al login.
    client.force_login(staff_user)
    response = client.get(reverse("dashboard:index"))
    assert response.status_code == 302
    assert "/admin/login/" in response.url


@pytest.mark.django_db
def test_superuser_accede(staff_client):
    response = staff_client.get(reverse("dashboard:index"))
    assert response.status_code == 200
