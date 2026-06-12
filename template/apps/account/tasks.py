"""Celery tasks per account app."""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_password_reset_email_task(_self, user_id):
    """
    Invia email di reset password in modo asincrono.

    Args:
        user_id: ID dell'utente
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for password reset")
        return

    # Token generation must happen here (cannot be serialised for a sub-task)
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:9000")
    reset_url = f"{frontend_url}/account/reset-password/{uidb64}/{token}/"
    valid_hours = settings.PASSWORD_RESET_TIMEOUT // 3600

    from apps.notifications.enums import NotificationEvent
    from apps.notifications.service import NotificationService

    NotificationService.send_notification(
        event=NotificationEvent.PASSWORD_RESET,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
            "reset_url": reset_url,
            "valid_hours": valid_hours,
        },
        recipient=user,
    )
    logger.info(f"Password reset notification dispatched for {user.email}")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_user_welcome_email_task(_self, user_id: int) -> None:
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for welcome email")
        return

    from apps.notifications.enums import NotificationEvent
    from apps.notifications.service import NotificationService

    NotificationService.send_notification(
        event=NotificationEvent.USER_WELCOME,
        recipient_email=user.email,
        context={"user_name": user.first_name or user.email},
        recipient=user,
    )
    logger.info(f"Welcome notification dispatched for {user.email}")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    retry_backoff=True,
)
def send_email_verification_task(_self, user_id: int) -> None:
    """Invia email di verifica indirizzo in modo asincrono."""
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for email verification")
        return

    if user.email_verified:
        logger.info(f"User {user_id} already verified, skipping")
        return

    from apps.account.tokens import email_verification_token

    token = email_verification_token.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:9000")
    verify_url = f"{frontend_url}/account/verify-email/{uidb64}/{token}/"

    from apps.notifications.enums import NotificationEvent
    from apps.notifications.service import NotificationService

    NotificationService.send_notification(
        event=NotificationEvent.EMAIL_VERIFICATION,
        recipient_email=user.email,
        context={
            "user_name": user.first_name or user.email,
            "verify_url": verify_url,
        },
        recipient=user,
    )
    logger.info(f"Email verification notification dispatched for {user.email}")
