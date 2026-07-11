from __future__ import annotations

from collections import OrderedDict
from typing import Any

from backend.app.config import TELEGRAM_SEND_ENABLED

DEFAULT_APPROVAL_STATE = "draft_pending"
DEFAULT_CARD_REVISION = 1

APPROVAL_ACTIONS_BY_STATE = {
    "draft_pending": OrderedDict(
        [
            ("Approve", "approve_draft"),
            ("Edit", "edit_draft"),
            ("Snooze", "snooze_draft"),
            ("Mark done", "mark_done"),
        ]
    ),
    "edit_requested": OrderedDict(
        [
            ("Approve", "approve_draft"),
            ("Mark done", "mark_done"),
        ]
    ),
    "snoozed": OrderedDict(
        [
            ("Approve", "approve_draft"),
            ("Mark done", "mark_done"),
        ]
    ),
    "approved_draft": OrderedDict(
        [
            ("Mark done", "mark_done"),
        ]
    ),
    "completed": OrderedDict(),
}

APPROVAL_ACTIONS = dict(APPROVAL_ACTIONS_BY_STATE[DEFAULT_APPROVAL_STATE])
APPROVAL_BUTTONS = list(APPROVAL_ACTIONS.keys())


def approval_actions_for_state(case_state: str | None) -> OrderedDict[str, str]:
    return APPROVAL_ACTIONS_BY_STATE.get(case_state or DEFAULT_APPROVAL_STATE, APPROVAL_ACTIONS_BY_STATE[DEFAULT_APPROVAL_STATE])


def approval_buttons_for_state(case_state: str | None) -> list[str]:
    return list(approval_actions_for_state(case_state).keys())


def build_callback_payload(case_id: str, card_revision: int, action: str) -> str:
    return f"disputepilot:{case_id}:{card_revision}:{action}"


def build_telegram_approval_markup(case_id: str, case_state: str | None, card_revision: int) -> dict[str, Any]:
    actions = approval_actions_for_state(case_state)
    return {
        "inline_keyboard": [
            [
                {
                    "text": label,
                    "callback_data": build_callback_payload(case_id, card_revision, action),
                }
                for label, action in actions.items()
            ]
        ]
        if actions
        else []
    }


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
    approval_state = case.get("approval_state") or DEFAULT_APPROVAL_STATE
    buttons = approval_buttons_for_state(approval_state)
    return {
        "preview_only": True,
        "send_enabled": TELEGRAM_SEND_ENABLED,
        "title": f"{case['case_id']}: {case['case_type']}",
        "body": " | ".join(body_parts),
        "buttons": buttons,
        "approval_buttons": buttons,
        "approval_state": approval_state,
        "card_revision": int(case.get("card_revision", DEFAULT_CARD_REVISION)),
    }


def _approval_body(case: dict[str, Any], case_state: str | None) -> str:
    deadline = None
    if case.get("extracted_deadlines"):
        deadline = case["extracted_deadlines"][0].get("date")

    body_parts = [
        f"Priority: {case.get('priority', 'unknown')}",
        f"Stage: {case.get('current_stage', 'unknown')}",
        f"Approval state: {case_state or DEFAULT_APPROVAL_STATE}",
    ]
    if deadline:
        body_parts.append(f"Deadline: {deadline}")
    body_parts.append(f"Next: {case.get('recommended_next_action', 'Review synthetic case.')}")
    return " | ".join(body_parts)


def build_telegram_approval_preview(
    case: dict[str, Any],
    *,
    case_state: str | None = None,
    card_revision: int = DEFAULT_CARD_REVISION,
) -> dict[str, Any]:
    resolved_state = case_state or case.get("approval_state") or DEFAULT_APPROVAL_STATE
    resolved_revision = int(case.get("card_revision", card_revision))
    buttons = approval_buttons_for_state(resolved_state)
    return {
        "preview_only": True,
        "send_enabled": TELEGRAM_SEND_ENABLED,
        "title": f"{case['case_id']}: {case['case_type']}",
        "body": _approval_body(case, resolved_state),
        "buttons": buttons,
        "approval_buttons": buttons,
        "card_revision": resolved_revision,
        "approval_state": resolved_state,
        "callback_data_example": build_callback_payload(case["case_id"], resolved_revision, approval_actions_for_state(resolved_state).get(buttons[0], "")) if buttons else None,
    }
