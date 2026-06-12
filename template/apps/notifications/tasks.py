import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=30,
    name="notifications.send_notification",
)
def send_notification_task(
    _self,
    event: str,
    recipient_email: str,
    context: dict,
    recipient_id: int | None = None,
    source_app_label: str | None = None,
    source_model: str | None = None,
    source_pk: int | None = None,
) -> None:
    """
    Unified async notification task.

    All parameters are JSON primitives (no ORM objects) for Celery serialisation.
    The task re-fetches User and source_object from the DB before dispatching.
    """
    from apps.notifications.service import NotificationService

    recipient = None
    if recipient_id is not None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            logger.warning("send_notification_task: user %s not found", recipient_id)

    source_object = None
    if source_app_label and source_model and source_pk:
        from django.apps import apps

        try:
            Model = apps.get_model(source_app_label, source_model)
            source_object = Model.objects.get(pk=source_pk)
        except Exception:
            # Source object missing is non-fatal — log is still written without it
            pass

    NotificationService.send_notification(
        event=event,
        recipient_email=recipient_email,
        context=context,
        recipient=recipient,
        source_object=source_object,
    )
