from django.contrib import admin

from apps.notifications.models import NotificationConfig, NotificationLog


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ["get_event_label", "email_enabled", "push_enabled"]
    list_editable = ["email_enabled", "push_enabled"]
    ordering = ["event"]

    @admin.display(description="Evento")
    def get_event_label(self, obj):
        return obj.get_event_display()

    def has_add_permission(self, _request):
        # Rows are seeded by migration — new events require a data migration, not manual admin adds.
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False

    def has_change_permission(self, request, _obj=None):
        return request.user.is_superuser

    def has_module_perms(self, request):
        return request.user.is_superuser


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_date",
        "get_event_label",
        "channel",
        "recipient_email",
        "status",
    ]
    list_filter = ["status", "channel", "event"]
    search_fields = ["recipient_email", "event"]
    date_hierarchy = "created_date"
    readonly_fields = [
        "event",
        "channel",
        "recipient",
        "recipient_email",
        "status",
        "error",
        "context_snapshot",
        "content_type",
        "object_id",
        "created_date",
        "modified_date",
    ]

    @admin.display(description="Evento")
    def get_event_label(self, obj):
        return obj.get_event_display()

    def has_add_permission(self, _request):
        return False

    def has_change_permission(self, _request, _obj=None):
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False
