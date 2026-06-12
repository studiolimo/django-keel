import pytest
from django.urls import reverse

from apps.users.models import User
from tests.conftest import TEST_PASSWORD


@pytest.fixture
def altro_utente(db):
    return User.objects.create_user(
        email="mario@example.com", password=TEST_PASSWORD,
        username="mario", first_name="Mario", last_name="Rossi",
    )


@pytest.mark.django_db
class TestUserList:
    def test_lista_renderizza(self, staff_client, altro_utente):
        response = staff_client.get(reverse("dashboard:user_list"))
        assert response.status_code == 200
        assert "mario@example.com" in response.content.decode()

    def test_filtro_per_email(self, staff_client, altro_utente, admin_user):
        response = staff_client.get(reverse("dashboard:user_list"), {"q": "mario"})
        html = response.content.decode()
        assert "mario@example.com" in html
        assert admin_user.email not in html

    def test_export_xlsx(self, staff_client, altro_utente):
        response = staff_client.get(reverse("dashboard:user_list"), {"download": "xlsx"})
        assert response.status_code == 200
        assert "spreadsheet" in response["Content-Type"]

    def test_azione_download_selezionati(self, staff_client, altro_utente):
        response = staff_client.post(
            reverse("dashboard:user_list"),
            {"action": "action_download_selected_rows", "selection": [altro_utente.pk]},
        )
        assert response.status_code == 200
        assert "spreadsheet" in response["Content-Type"]

    def test_filtro_per_membership(self, staff_client, altro_utente):
        response = staff_client.get(reverse("dashboard:user_list"), {"membership": "free"})
        assert "mario@example.com" in response.content.decode()

    def test_azione_non_dichiarata_ignorata(self, staff_client, altro_utente):
        # action_delete_objects esiste sui mixin ma NON è dichiarata in actions:
        # il POST forgiato non deve eliminare nulla.
        response = staff_client.post(
            reverse("dashboard:user_list"),
            {"action": "action_delete_objects", "post": "yes", "selection": [altro_utente.pk]},
        )
        assert response.status_code == 200
        assert User.objects.filter(pk=altro_utente.pk).exists()

    def test_post_senza_azione_non_crasha(self, staff_client, altro_utente):
        response = staff_client.post(reverse("dashboard:user_list"), {})
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserEdit:
    def test_form_renderizza(self, staff_client, altro_utente):
        response = staff_client.get(reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk}))
        assert response.status_code == 200

    def test_salvataggio_modifica(self, staff_client, altro_utente):
        response = staff_client.post(
            reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk}),
            {
                "username": "mario", "first_name": "Mario", "last_name": "Verdi",
                "email_verified": "on", "is_active": "on",
            },
        )
        assert response.status_code == 302
        altro_utente.refresh_from_db()
        assert altro_utente.last_name == "Verdi"

    def test_salva_e_continua_resta_sulla_pagina(self, staff_client, altro_utente):
        response = staff_client.post(
            reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk}),
            {
                "username": "mario", "first_name": "Mario", "last_name": "Rossi",
                "is_active": "on", "save_and_continue": "1",
            },
        )
        assert response.status_code == 302
        assert response.url == reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk})

    def test_edit_pk_inesistente_404(self, staff_client):
        response = staff_client.get(reverse("dashboard:user_edit", kwargs={"pk": 999999}))
        assert response.status_code == 404

    def test_form_invalido_re_renderizza(self, staff_client, altro_utente):
        # first_name oltre max_length (256) → form_invalid → 200 con errori
        response = staff_client.post(
            reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk}),
            {"username": "mario", "first_name": "x" * 300, "last_name": "Rossi", "is_active": "on"},
        )
        assert response.status_code == 200
        altro_utente.refresh_from_db()
        assert altro_utente.first_name == "Mario"


@pytest.mark.django_db
class TestUserDelete:
    def test_eliminazione_via_post(self, staff_client, altro_utente):
        response = staff_client.post(
            reverse("dashboard:user_delete", kwargs={"pk": altro_utente.pk}),
            HTTP_REFERER=reverse("dashboard:user_list"),
        )
        assert response.status_code == 302
        assert not User.objects.filter(pk=altro_utente.pk).exists()

    def test_eliminazione_senza_referer_non_crasha(self, staff_client, altro_utente):
        response = staff_client.post(reverse("dashboard:user_delete", kwargs={"pk": altro_utente.pk}))
        assert response.status_code == 302
        assert not User.objects.filter(pk=altro_utente.pk).exists()

    def test_get_non_elimina(self, staff_client, altro_utente):
        response = staff_client.get(reverse("dashboard:user_delete", kwargs={"pk": altro_utente.pk}))
        assert response.status_code == 405
        assert User.objects.filter(pk=altro_utente.pk).exists()

    def test_delete_pk_inesistente_404(self, staff_client):
        response = staff_client.post(reverse("dashboard:user_delete", kwargs={"pk": 999999}))
        assert response.status_code == 404

    def test_redirect_url_dal_post_ha_priorita(self, staff_client, altro_utente):
        lista = reverse("dashboard:user_list")
        response = staff_client.post(
            reverse("dashboard:user_delete", kwargs={"pk": altro_utente.pk}),
            {"redirect_url": lista},
            HTTP_REFERER=reverse("dashboard:user_edit", kwargs={"pk": altro_utente.pk}),
        )
        assert response.status_code == 302
        assert response.url == lista

    def test_redirect_url_esterno_ripiega_su_index(self, staff_client, altro_utente):
        response = staff_client.post(
            reverse("dashboard:user_delete", kwargs={"pk": altro_utente.pk}),
            {"redirect_url": "https://evil.example.com/"},
        )
        assert response.status_code == 302
        assert response.url == reverse("dashboard:index")
