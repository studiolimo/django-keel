import django_filters
from crispy_forms.layout import Column, Field, Layout, Row, Submit
from django.db.models import Q

from apps.dashboard.crispy_layout import Card
from apps.dashboard.forms import DashboardFormHelper
from apps.dashboard.mixins import CreateUpdateFormMixin
from apps.users.models import User


class UserFilterFormHelper(DashboardFormHelper):
    form_method = "GET"
    layout = Layout(
        Row(
            Column(Field("q")),
            Column(Field("membership")),
            Column(Field("email_verified")),
            css_class="grid gap-4 sm:grid-cols-3",
        ),
        Submit("submit", "Applica filtri", css_class="mt-3"),
    )


class UserFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filtra_testo", label="Cerca")

    class Meta:
        model = User
        fields = ["membership", "email_verified"]

    def filtra_testo(self, queryset, name, value):  # noqa: ARG002
        return queryset.filter(
            Q(email__icontains=value)
            | Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        )


class UserUpdateForm(CreateUpdateFormMixin):
    class Meta:
        model = User
        fields = [
            "email", "username", "first_name", "last_name",
            "email_verified", "profile_complete", "marketing_consent",
            "force_premium", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email in sola lettura: il cambio email passa dal flusso dedicato dell'app
        # (con verifica). disabled=True ignora il POST e usa il valore dell'istanza.
        self.fields["email"].disabled = True

    def get_form_layout(self):
        return Layout(
            Card(
                "email", "username", "first_name", "last_name",
                title="Anagrafica",
            ),
            Card(
                "email_verified", "profile_complete", "marketing_consent",
                "force_premium", "is_active",
                title="Stato account",
            ),
        )
