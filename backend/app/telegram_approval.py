from __future__ import annotations

from typing import Any

from backend.app.config import TELEGRAM_SEND_ENABLED
from backend.app.telegram_preview import APPROVAL_BUTTONS

REPLY_CHANNEL = "Telegram topic/thread"


def build_telegram_approval_preview(case: dict[str, Any]) -> dict[str, Any]:
    deadline = None
    deadlines = case.get("extracted_deadlines") or []
    if deadlines:
        deadline = deadlines[0].get("date")
    return {
        "preview_only": True,
        "send_enabled": TELEGRAM_SEND_ENABLED,
        "reply_channel": REPLY_CHANNEL,
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "priority": case.get("priority", "unknown"),
        "deadline": deadline,
        "approval_buttons": APPROVAL_BUTTONS,
        "response_prompt": f"Approve the synthetic reply for {case['case_id']} or ask for a review escalation.",
        "escalation_rule": "If the human does not act before the deadline, keep the case open and flag it for follow-up.",
        "buttons": APPROVAL_BUTTONS,
    }
