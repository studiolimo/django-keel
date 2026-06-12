from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.mixins import TimeStampedMixin
from apps.notifications.enums import NotificationChannel, NotificationEvent


class NotificationConfig(TimeStampedMixin):
    """
    Per-event channel configuration. One row per NotificationEvent.

    Rows are seeded by migration — do not add/delete from admin.
    When adding a new NotificationEvent, add a corresponding row via data migration.
    """

    event = models.CharField(
        max_length=60,
        choices=NotificationEvent.choices,
        unique=True,
        verbose_name="Evento",
    )
    email_enabled = models.BooleanField(default=True, verbose_name="Email abilitata")
    push_enabled = models.BooleanField(default=False, verbose_name="Push abilitata")

    class Meta:
        ordering = ["event"]
        verbose_name = "Configurazione notifica"
        verbose_name_plural = "Configurazioni notifiche"

    def __str__(self) -> str:
        return self.get_event_display()  # type: ignore[return-value]

    def active_channels(self) -> list[str]:
        channels: list[str] = []
        if self.email_enabled:
            channels.append(NotificationChannel.EMAIL)
        if self.push_enabled:
            channels.append(NotificationChannel.PUSH)
        return channels


class NotificationLogStatus(models.TextChoices):
    SENT = "sent", "Inviato"
    FAILED = "failed", "Fallito"
    SKIPPED = "skipped", "Saltato"


class NotificationLog(TimeStampedMixin):
    """Audit record for every notification send attempt."""

    event = models.CharField(
        max_length=60,
        choices=NotificationEvent.choices,
        db_index=True,
        verbose_name="Evento",
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        verbose_name="Canale",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name="Destinatario",
    )
    # Denormalizzato: sopravvive alla cancellazione dell'utente
    recipient_email = models.EmailField(blank=True, verbose_name="Email destinatario")
    status = models.CharField(
        max_length=20,
        choices=NotificationLogStatus.choices,
        default=NotificationLogStatus.SENT,
        db_index=True,
        verbose_name="Stato",
    )
    error = models.TextField(blank=True, verbose_name="Errore")
    # Solo valori scalari (no oggetti ORM) per evitare problemi di serializzazione
    context_snapshot = models.JSONField(default=dict, verbose_name="Snapshot contesto")

    # GenericFK verso il source object (Booking, SpecialistRequest, GiftCard, ...)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["recipient", "-created_date"]),
        ]
        verbose_name = "Log notifica"
        verbose_name_plural = "Log notifiche"

    def __str__(self) -> str:
        return f"[{self.channel}] {self.event} → {self.recipient_email} ({self.status})"
