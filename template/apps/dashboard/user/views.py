from django.urls import reverse_lazy

from apps.dashboard.mixins import (
    CreateUpdateMixin,
    DeleteMixin,
    ListViewMixin,
    SuperuserPermissionMixin,
)
from apps.users.models import User

from .forms import UserFilter, UserFilterFormHelper, UserUpdateForm
from .tables import UserTable, UserTableExport


class UserListView(SuperuserPermissionMixin, ListViewMixin):
    model = User
    table_class = UserTable
    export_table_class = UserTableExport
    formhelper_class = UserFilterFormHelper
    filterset_class = UserFilter
    actions = [
        {"fn": "action_download_selected_rows", "description": "Scarica righe selezionate (xlsx)"},
    ]
    ordering = "-date_joined"
    page_title = "Utenti"


class UserUpdateView(SuperuserPermissionMixin, CreateUpdateMixin):
    model = User
    form_class = UserUpdateForm
    success_url = reverse_lazy("dashboard:user_list")
    edit_url_name = "user_edit"
    delete_url_name = "user_delete"


class UserDeleteView(SuperuserPermissionMixin, DeleteMixin):
    model = User
