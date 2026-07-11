from __future__ import annotations

from typing import Any

from backend.app.telegram_preview import build_telegram_approval_preview as _build_telegram_approval_preview

REPLY_CHANNEL = "Telegram topic/thread"


def build_telegram_approval_preview(case: dict[str, Any], *, case_state: str | None = None, card_revision: int = 1) -> dict[str, Any]:
    preview = _build_telegram_approval_preview(case, case_state=case_state, card_revision=card_revision)
    preview.update(
        {
            "reply_channel": REPLY_CHANNEL,
            "response_prompt": f"Approve the synthetic reply for {case['case_id']} or ask for a review escalation.",
            "escalation_rule": "If the human does not act before the deadline, keep the case open and flag it for follow-up.",
        }
    )
    return preview
