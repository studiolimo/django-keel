from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationEvent(models.TextChoices):
    # Booking lifecycle
    BOOKING_CONFIRMED_USER = "booking_confirmed_user", _("Prenotazione confermata (Utente)")
    BOOKING_CONFIRMED_SPECIALIST = (
        "booking_confirmed_specialist",
        _("Nuova prenotazione (Specialist)"),
    )
    BOOKING_CANCELLED_USER = "booking_cancelled_user", _("Prenotazione cancellata (Utente)")
    BOOKING_CANCELLED_SPECIALIST = (
        "booking_cancelled_specialist",
        _("Prenotazione cancellata (Specialist)"),
    )
    BOOKING_STATUS_CHANGE_USER = (
        "booking_status_change_user",
        _("Aggiornamento prenotazione (Utente)"),
    )
    BOOKING_REMINDER_USER = "booking_reminder_user", _("Promemoria prenotazione (Utente)")

    # Specialist onboarding
    SPECIALIST_REQUEST_SUBMITTED = (
        "specialist_request_submitted",
        _("Nuova richiesta specialist (Admin)"),
    )
    SPECIALIST_REQUEST_ACCEPTED = "specialist_request_accepted", _("Richiesta specialist approvata")
    SPECIALIST_REQUEST_REJECTED = "specialist_request_rejected", _("Richiesta specialist rifiutata")
    SPECIALIST_WELCOME = "specialist_welcome", _("Benvenuto specialist")

    # Payments / gift cards
    GIFT_CARD_RECEIVED = "gift_card_received", _("Gift card ricevuta")
    PAYMENT_REFUND_ISSUED = "payment_refund_issued", _("Rimborso / credito emesso")

    # Account
    PASSWORD_RESET = "password_reset", _("Reset password")
    USER_WELCOME = "user_welcome", _("Benvenuto")
    EMAIL_VERIFICATION = "email_verification", "Email Verification"

    # Messaging
    NEW_MESSAGE_RECEIVED = "new_message_received", _("Nuovo messaggio ricevuto")


class NotificationChannel(models.TextChoices):
    EMAIL = "email", _("Email")
    PUSH = "push", _("Push Notification")
