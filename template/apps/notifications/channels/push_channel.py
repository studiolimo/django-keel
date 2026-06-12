import logging
from typing import Any

from apps.notifications.channels.base import AbstractChannel
from apps.notifications.enums import NotificationChannel

logger = logging.getLogger(__name__)

# Populate this set with NotificationEvent values when FCM/OneSignal is integrated.
# While empty, every push attempt is logged as 'skipped' (not an error).
PUSH_ENABLED_EVENTS: set[str] = set()


class PushChannel(AbstractChannel):
    """
    Stub push notification channel. Ready for FCM or OneSignal integration.

    To activate:
    1. Add FCM_API_KEY (or ONESIGNAL_APP_ID + ONESIGNAL_API_KEY) to settings
    2. Add a UserDevice model (user FK, token, platform) to store device tokens
    3. Implement the send() body below
    4. Populate PUSH_ENABLED_EVENTS with the desired NotificationEvent values
    """

    channel_type = NotificationChannel.PUSH

    def send(
        self,
        event: str,
        recipient_email: str,  # noqa: ARG002
        context: dict[str, Any],  # noqa: ARG002
        recipient=None,  # noqa: ARG002
    ) -> bool:
        if event not in PUSH_ENABLED_EVENTS:
            # Not yet wired up — signal 'skipped', not a failure
            return False

        # --- Future implementation ---
        # from apps.notifications.models import UserDevice
        # tokens = UserDevice.objects.filter(user=recipient, is_active=True)
        # for device in tokens:
        #     push_client.send(
        #         token=device.token,
        #         title=_build_push_title(event, context),
        #         body=_build_push_body(event, context),
        #         data={"event": event, **context},
        #     )
        # return True

        logger.debug("PushChannel: event '%s' not yet implemented", event)
        return False
