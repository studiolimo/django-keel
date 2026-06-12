import logging
from typing import Any

from apps.notifications.channels.base import AbstractChannel
from apps.notifications.enums import NotificationChannel

logger = logging.getLogger(__name__)


class EmailChannel(AbstractChannel):
    """Sends emails by looking up the appropriate EmailTemplate subclass in the registry."""

    channel_type = NotificationChannel.EMAIL

    def send(
        self,
        event: str,
        recipient_email: str,
        context: dict[str, Any],
        recipient=None,  # noqa: ARG002
    ) -> bool:
        # Import here to avoid circular imports at module load time
        from apps.notifications.email_classes import EMAIL_CLASS_REGISTRY

        email_class = EMAIL_CLASS_REGISTRY.get(event)
        if email_class is None:
            logger.warning("EmailChannel: no template class registered for event '%s'", event)
            return False

        email = email_class(to_email=recipient_email, context=context)
        # Let exceptions propagate — NotificationService will catch and log status=failed
        email.send(fail_silently=False)
        return True
