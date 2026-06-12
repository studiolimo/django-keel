from django.conf import settings
from django.db import models

from apps.core.mixins import TimeStampedMixin


class SocialProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    FACEBOOK = "facebook", "Facebook"
    APPLE = "apple", "Apple"


class SocialAccount(TimeStampedMixin):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=SocialProvider.choices)
    provider_uid = models.CharField(max_length=255)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("provider", "provider_uid")

    def __str__(self):
        return f"{self.provider} - {self.user.email}"


class LegalDocumentType(models.TextChoices):
    TERMS = "terms", "Termini di Servizio"
    PRIVACY = "privacy", "Informativa sulla Privacy"


class LegalDocument(TimeStampedMixin):
    document_type = models.CharField(max_length=20, choices=LegalDocumentType.choices)
    version_label = models.CharField(max_length=50)
    effective_date = models.DateField()

    class Meta:
        ordering = ["-effective_date"]
        unique_together = ("document_type", "effective_date")

    def __str__(self) -> str:
        return f"{self.document_type} {self.version_label}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
