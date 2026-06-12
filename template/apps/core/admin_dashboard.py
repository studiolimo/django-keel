from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)

# Status badge colors for Booking.status
STATUS_COLORS = {
    "pending": "yellow",
    "pending_payment": "orange",
    "confirmed": "blue",
    "completed": "green",
    "cancelled": "red",
}


def get_kpi_cards() -> list[dict[str, Any]]:
    return [
        {
            "id": "fake_one",
            "label": "Fake",
            "value": [],
            "icon": "calendar_today",
            "type": "number",
        },
    ]


def dashboard_callback(request: Any, context: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    _SECTIONS: list[tuple[str, Any, Any]] = [
        ("kpi_cards", get_kpi_cards, []),
    ]
    for key, fn, fallback in _SECTIONS:
        try:
            context[key] = fn()
        except Exception:
            logger.exception("Admin dashboard: error computing '%s'", key)
            context[key] = fallback
    return context
