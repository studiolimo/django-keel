from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.admin import ModelAdmin

from apps.account.models import LegalDocument, SocialAccount

User = get_user_model()


@admin.register(SocialAccount)
class SocialAccountAdmin(ModelAdmin):
    list_display = ("user", "provider", "provider_uid", "created_date")
    list_filter = ("provider",)
    search_fields = ("user__email", "provider_uid")
    raw_id_fields = ("user",)


@admin.register(LegalDocument)
class LegalDocumentAdmin(ModelAdmin):
    list_display = ("document_type", "version_label", "effective_date", "created_date")
    list_filter = ("document_type",)
    readonly_fields = ("created_date", "modified_date")


@admin.register(Session)
class SessionAdmin(ModelAdmin):
    # Ceates an easy way to view/expire current sessions
    list_display = ("session_key", "username", "expire_date")

    def username(self, obj):
        session_data = obj.get_decoded()
        user_id = session_data.get("_auth_user_id")

        if user_id:
            user = User.objects.get(id=user_id)
            return user.username
        return None
