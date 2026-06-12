"""
NotificationService — central channel-agnostic notification dispatcher.

Usage from any Celery task or view:

    from apps.notifications.service import notify_booking_confirmed
    notify_booking_confirmed(booking)

Each notify_* helper builds a flat JSON-safe context and enqueues
send_notification_task.delay() for each recipient.
"""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.notifications.enums import NotificationChannel, NotificationEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel + event routing
# ---------------------------------------------------------------------------


# Instantiated once at module level — stateless objects, safe to share.
def _get_channels() -> list:
    from apps.notifications.channels.email_channel import EmailChannel
    from apps.notifications.channels.push_channel import PushChannel

    return [EmailChannel(), PushChannel()]


def _get_active_channels(event: str) -> list[str]:
    """
    Return the list of active channels for the given event, reading from NotificationConfig.
    Falls back to email-only with a warning if the config row is missing.
    When adding a new NotificationEvent, add the corresponding row via data migration.
    """
    from apps.notifications.models import NotificationConfig

    try:
        config = NotificationConfig.objects.get(event=event)
        return config.active_channels()
    except NotificationConfig.DoesNotExist:
        logger.warning(
            "NotificationConfig missing for event=%s — falling back to email-only. "
            "Add a data migration to seed this event.",
            event,
        )
        return [NotificationChannel.EMAIL]


# ---------------------------------------------------------------------------
# Core dispatcher
# ---------------------------------------------------------------------------


class NotificationService:
    """
    Static service that dispatches a notification across all active channels
    and writes a NotificationLog entry for each attempt.
    """

    @staticmethod
    def send_notification(
        event: str,
        recipient_email: str,
        context: dict[str, Any],
        recipient=None,
        source_object: models.Model | None = None,
    ) -> None:
        from apps.notifications.models import NotificationLog, NotificationLogStatus

        active_channel_types = _get_active_channels(event)
        channels = {ch.channel_type: ch for ch in _get_channels()}

        # Resolve content type for GenericFK
        content_type = None
        object_id = None
        if source_object is not None:
            from django.contrib.contenttypes.models import ContentType

            content_type = ContentType.objects.get_for_model(source_object)
            object_id = source_object.pk

        for channel_type in active_channel_types:
            channel = channels.get(channel_type)
            if channel is None:
                continue

            log_data: dict[str, Any] = {
                "event": event,
                "channel": channel_type,
                "recipient": recipient,
                "recipient_email": recipient_email,
                "context_snapshot": _build_snapshot(context),
                "content_type": content_type,
                "object_id": object_id,
            }

            try:
                result = channel.send(
                    event=event,
                    recipient_email=recipient_email,
                    context=context,
                    recipient=recipient,
                )
                log_data["status"] = (
                    NotificationLogStatus.SKIPPED if result is False else NotificationLogStatus.SENT
                )
            except Exception as exc:
                log_data["status"] = NotificationLogStatus.FAILED
                log_data["error"] = str(exc)
                logger.error(
                    "Notification failed: event=%s channel=%s recipient=%s error=%s",
                    event,
                    channel_type,
                    recipient_email,
                    exc,
                )

            NotificationLog.objects.create(**log_data)


# ---------------------------------------------------------------------------
# Context builders (flat, JSON-safe)
# ---------------------------------------------------------------------------


def _build_snapshot(context: dict[str, Any]) -> dict[str, Any]:
    """Keep only JSON-serialisable scalar values for the audit log."""
    return {
        k: v for k, v in context.items() if isinstance(v, str | int | float | bool | type(None))
    }


def _booking_context(booking) -> dict[str, Any]:
    # User name: handle manual bookings with no linked user
    if booking.user is not None:
        user_name = (
            f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.email
        )
    else:
        user_name = (
            f"{booking.manual_client_nome} {booking.manual_client_cognome}".strip()
            or booking.manual_client_email
            or ""
        )

    # Specialist: prefer service.specialist (regular) then booking.specialist (manual)
    specialist_name = ""
    specialist_email = ""
    price = ""

    if booking.service is not None:
        specialist_user = booking.service.specialist.user
        specialist_name = (
            f"{specialist_user.first_name} {specialist_user.last_name}".strip()
            or specialist_user.email
        )
        specialist_email = specialist_user.email
        price = booking.service.get_price_text()
    elif booking.specialist is not None:
        specialist_user = booking.specialist.user
        specialist_name = (
            f"{specialist_user.first_name} {specialist_user.last_name}".strip()
            or specialist_user.email
        )
        specialist_email = specialist_user.email
        price = (
            "Gratis"
            if booking.service_price == 0
            else (f"€{booking.service_price}" if booking.service_price is not None else "")
        )

    # Calcola le policy di cancellazione tramite CancellationPolicyService
    from apps.bookings.models import BookingType
    from apps.bookings.utils.cancellation import CancellationPolicyService

    cancellation_policies = []
    if booking.booking_type != BookingType.MANUAL and booking.service:
        booking_start = timezone.make_aware(datetime.combine(booking.date, booking.start_time))
        reference = booking.created_date or timezone.now()
        cancellation_policies = CancellationPolicyService(
            booking.service, booking_start, reference
        ).get_policies()

    # Build Google Calendar link (same logic as frontend calendarHelpers.js)
    fmt_date = booking.date.strftime("%Y%m%d")
    location_str = ", ".join(filter(None, [booking.location_name, booking.location_address]))
    google_calendar_url = "https://calendar.google.com/calendar/render?" + urlencode(
        {
            "action": "TEMPLATE",
            "text": booking.service_name or "",
            "dates": f"{fmt_date}T{booking.start_time.strftime('%H%M%S')}/{fmt_date}T{booking.end_time.strftime('%H%M%S')}",
            "details": f"Prenotazione #{booking.code} con {specialist_name}",
            "location": location_str,
        }
    )

    return {
        "user_name": user_name,
        "specialist_name": specialist_name,
        "specialist_email": specialist_email,
        "booking_code": booking.code,
        "service_name": booking.service_name or "",
        "date": booking.date.strftime("%d/%m/%Y"),
        "start_time": booking.start_time.strftime("%H:%M"),
        "end_time": booking.end_time.strftime("%H:%M"),
        "price": price,
        "location_name": booking.location_name or "",
        "location_address": booking.location_address or "",
        "cancellation_policies": cancellation_policies,
        "google_calendar_url": google_calendar_url,
    }


# ---------------------------------------------------------------------------
# Public helpers — one per logical notification action
# ---------------------------------------------------------------------------


def notify_booking_confirmed(booking) -> None:
    """Enqueue confirmation emails to both user/client and specialist."""
    from apps.notifications.tasks import send_notification_task

    ctx = _booking_context(booking)

    # User notification: linked user or manual client email
    if booking.user is not None:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CONFIRMED_USER,
            recipient_email=booking.user.email,
            context=ctx,
            recipient_id=booking.user_id,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )
    elif booking.manual_client_email:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CONFIRMED_USER,
            recipient_email=booking.manual_client_email,
            context=ctx,
            recipient_id=None,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )

    # Specialist notification (space_direct has neither service nor specialist)
    specialist = None
    if booking.service is not None:
        specialist = booking.service.specialist
    elif booking.specialist is not None:
        specialist = booking.specialist

    if specialist is not None:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CONFIRMED_SPECIALIST,
            recipient_email=specialist.user.email,
            context=ctx,
            recipient_id=specialist.user_id,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )


def notify_booking_cancelled(booking, cancelled_by: str = "user") -> None:
    """Enqueue cancellation emails to both user/client and specialist."""
    from apps.notifications.tasks import send_notification_task

    ctx = _booking_context(booking)
    ctx["cancellation_reason"] = booking.cancellation_reason or ""
    ctx["cancelled_by"] = cancelled_by

    # User notification: linked user or manual client email
    if booking.user is not None:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CANCELLED_USER,
            recipient_email=booking.user.email,
            context=ctx,
            recipient_id=booking.user_id,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )
    elif booking.manual_client_email:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CANCELLED_USER,
            recipient_email=booking.manual_client_email,
            context=ctx,
            recipient_id=None,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )

    # Specialist notification (space_direct has neither service nor specialist)
    specialist = None
    if booking.service is not None:
        specialist = booking.service.specialist
    elif booking.specialist is not None:
        specialist = booking.specialist

    if specialist is not None:
        send_notification_task.delay(
            event=NotificationEvent.BOOKING_CANCELLED_SPECIALIST,
            recipient_email=specialist.user.email,
            context=ctx,
            recipient_id=specialist.user_id,
            source_app_label="bookings",
            source_model="Booking",
            source_pk=booking.pk,
        )


def notify_booking_status_change(booking, new_status: str) -> None:
    from apps.notifications.tasks import send_notification_task

    ctx = _booking_context(booking)
    ctx["new_status"] = new_status
    ctx["status_display"] = booking.get_status_display()

    send_notification_task.delay(
        event=NotificationEvent.BOOKING_STATUS_CHANGE_USER,
        recipient_email=booking.user.email,
        context=ctx,
        recipient_id=booking.user_id,
        source_app_label="bookings",
        source_model="Booking",
        source_pk=booking.pk,
    )


def notify_specialist_request_submitted(user) -> None:
    """Notify admin (SUPPORT_EMAIL) of a new specialist request."""
    from apps.notifications.tasks import send_notification_task

    send_notification_task.delay(
        event=NotificationEvent.SPECIALIST_REQUEST_SUBMITTED,
        recipient_email=settings.SUPPORT_EMAIL,
        context={
            "user_email": user.email,
            "user_name": user.get_full_name() or user.email,
            "phone": str(user.phone) if user.phone else "",
        },
        recipient_id=None,
    )


def notify_specialist_request_accepted(specialist_request) -> None:
    from apps.notifications.tasks import send_notification_task

    user = specialist_request.user
    send_notification_task.delay(
        event=NotificationEvent.SPECIALIST_REQUEST_ACCEPTED,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
            "payment_link": specialist_request.payment_link or "",
        },
        recipient_id=user.pk,
        source_app_label="users",
        source_model="SpecialistRequest",
        source_pk=specialist_request.pk,
    )


def notify_specialist_request_rejected(specialist_request) -> None:
    from apps.notifications.tasks import send_notification_task

    user = specialist_request.user
    send_notification_task.delay(
        event=NotificationEvent.SPECIALIST_REQUEST_REJECTED,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
        },
        recipient_id=user.pk,
        source_app_label="users",
        source_model="SpecialistRequest",
        source_pk=specialist_request.pk,
    )


def notify_specialist_welcome(specialist) -> None:
    from apps.notifications.tasks import send_notification_task

    user = specialist.user
    send_notification_task.delay(
        event=NotificationEvent.SPECIALIST_WELCOME,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
        },
        recipient_id=user.pk,
        source_app_label="users",
        source_model="Specialist",
        source_pk=specialist.pk,
    )


def notify_gift_card_received(gift_card) -> None:
    from apps.notifications.tasks import send_notification_task

    buyer = gift_card.purchased_by
    buyer_name = f"{buyer.first_name} {buyer.last_name}".strip() or buyer.email if buyer else ""

    send_notification_task.delay(
        event=NotificationEvent.GIFT_CARD_RECEIVED,
        recipient_email=gift_card.recipient_email,
        context={
            "buyer_name": buyer_name,
            "amount": str(gift_card.initial_balance),
            "code": gift_card.code,
            "expires_at": (
                gift_card.expires_at.strftime("%d/%m/%Y") if gift_card.expires_at else ""
            ),
        },
        recipient_id=None,
        source_app_label="payments",
        source_model="GiftCard",
        source_pk=gift_card.pk,
    )


def notify_password_reset(user, reset_url: str, valid_hours: int) -> None:
    from apps.notifications.tasks import send_notification_task

    send_notification_task.delay(
        event=NotificationEvent.PASSWORD_RESET,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
            "reset_url": reset_url,
            "valid_hours": valid_hours,
        },
        recipient_id=user.pk,
    )


def notify_user_welcome(user) -> None:
    from apps.notifications.tasks import send_notification_task

    send_notification_task.delay(
        event=NotificationEvent.USER_WELCOME,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
        },
        recipient_id=user.pk,
    )


def notify_new_message_received(conversation, recipient) -> None:
    """
    Called from messaging tasks when a new message notification needs to be sent.
    NOTE: Typically not called directly — the messaging Celery task calls
    NotificationService.send_notification() directly after its unread-check logic.
    This helper is provided for future use (e.g. admin triggers).
    """
    from apps.notifications.tasks import send_notification_task

    if conversation.user == recipient:
        sender_user = conversation.specialist.user
    else:
        sender_user = conversation.user
    sender_name = sender_user.get_full_name() or sender_user.email

    send_notification_task.delay(
        event=NotificationEvent.NEW_MESSAGE_RECEIVED,
        recipient_email=recipient.email,
        context={
            "user_name": recipient.first_name or recipient.email,
            "sender_name": sender_name,
            "conversation_url": f"{settings.FRONTEND_URL}/messaggi/{conversation.id}",
            "service_name": conversation.service.name if conversation.service else "",
        },
        recipient_id=recipient.pk,
        source_app_label="messaging",
        source_model="Conversation",
        source_pk=str(conversation.pk),
    )
