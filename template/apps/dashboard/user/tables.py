import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from apps.dashboard.mixins import TableMultiSelectMixin
from apps.users.models import User


class UserTable(TableMultiSelectMixin, tables.Table):
    email = tables.Column(linkify=lambda record: reverse("dashboard:user_edit", kwargs={"pk": record.pk}))
    nome = tables.Column(accessor="first_name", verbose_name="Nome", order_by=("first_name", "last_name"))
    membership = tables.Column()
    email_verified = tables.BooleanColumn(verbose_name="Email verificata")
    date_joined = tables.DateTimeColumn(verbose_name="Registrato il", format="d/m/Y H:i")

    class Meta:
        model = User
        fields = ("email", "username", "membership", "email_verified", "date_joined")
        sequence = ("selection", "email", "username", "nome", "membership", "email_verified", "date_joined")

    def render_nome(self, record):
        return f"{record.first_name} {record.last_name}".strip() or "—"

    def render_membership(self, value):
        if value == "premium":
            return format_html(
                '<span class="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium">{}</span>',
                "premium",
            )
        return format_html(
            '<span class="rounded-full bg-paper px-2 py-0.5 text-xs text-ink-faint border border-line">{}</span>',
            "free",
        )


class UserTableExport(tables.Table):
    class Meta:
        model = User
        fields = (
            "email", "username", "first_name", "last_name", "membership",
            "email_verified", "profile_complete", "marketing_consent", "is_active", "date_joined",
        )
