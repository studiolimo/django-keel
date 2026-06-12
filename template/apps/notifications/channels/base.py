from abc import ABC, abstractmethod
from typing import Any


class AbstractChannel(ABC):
    """
    Interface that all notification channels must implement.
    Called by NotificationService after it resolves which channels handle an event.
    """

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Return the NotificationChannel value (e.g. 'email')."""
        ...

    @abstractmethod
    def send(
        self,
        event: str,
        recipient_email: str,
        context: dict[str, Any],
        recipient=None,
    ) -> bool:
        """
        Send the notification for the given event.

        Returns True on success, False to signal 'skipped' (not an error).
        Raises on hard failures so the caller can log status='failed'.
        """
        ...
