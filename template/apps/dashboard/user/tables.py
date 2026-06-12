import django_tables2 as tables
from django.urls import reverse

from apps.dashboard.mixins import TableMultiSelectMixin
from apps.users.models import User


class UserTable(TableMultiSelectMixin, tables.Table):
    email = tables.Column(linkify=lambda record: reverse("dashboard:user_edit", kwargs={"pk": record.pk}))
    nome = tables.Column(accessor="first_name", verbose_name="Nome", order_by=("first_name", "last_name"))
    email_verified = tables.BooleanColumn(verbose_name="Email verificata")
    date_joined = tables.DateTimeColumn(verbose_name="Registrato il", format="d/m/Y H:i")

    class Meta:
        model = User
        fields = ("email", "username", "email_verified", "date_joined")
        sequence = ("selection", "email", "username", "nome", "email_verified", "date_joined")

    def render_nome(self, record):
        return f"{record.first_name} {record.last_name}".strip() or "—"


class UserTableExport(tables.Table):
    class Meta:
        model = User
        fields = (
            "email", "username", "first_name", "last_name",
            "email_verified", "profile_complete", "marketing_consent", "is_active", "date_joined",
        )
