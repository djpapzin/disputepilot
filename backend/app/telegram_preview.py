from __future__ import annotations

from typing import Any

from backend.app.config import TELEGRAM_SEND_ENABLED

APPROVAL_BUTTONS = ["Approve Draft", "Edit Draft", "Snooze", "Mark Resolved", "Request Evidence"]


def build_telegram_card_preview(case: dict[str, Any]) -> dict[str, Any]:
    deadline = None
    if case.get("extracted_deadlines"):
        deadline = case["extracted_deadlines"][0].get("date")
    body_parts = [
        f"Priority: {case.get('priority', 'unknown')}",
        f"Stage: {case.get('current_stage', 'unknown')}",
    ]
    if deadline:
        body_parts.append(f"Deadline: {deadline}")
    body_parts.append(f"Next: {case.get('recommended_next_action', 'Review synthetic case.')}")
    return {
        "preview_only": True,
        "send_enabled": TELEGRAM_SEND_ENABLED,
        "title": f"{case['case_id']}: {case['case_type']}",
        "body": " | ".join(body_parts),
        "buttons": APPROVAL_BUTTONS,
    }
