import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_shell_renderizza_sidebar_e_topbar(staff_client):
    response = staff_client.get(reverse("dashboard:index"))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="sidebar"' in html
    assert 'id="topbar"' in html
    assert "dashboard/css/dashboard.css" in html
    assert "dashboard/js/dashboard.js" in html


@pytest.mark.django_db
def test_messages_renderizzate(staff_client):
    # la pagina include il blocco messaggi anche da vuoto
    response = staff_client.get(reverse("dashboard:index"))
    assert 'id="dj-messages"' in response.content.decode()


@pytest.mark.django_db
def test_dialog_conferma_presente(staff_client):
    # Il dialog globale di conferma (Alpine store) deve essere nel DOM di ogni pagina.
    html = staff_client.get(reverse("dashboard:index")).content.decode()
    assert "$store.confirm.open" in html
    assert 'role="dialog"' in html
