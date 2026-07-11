from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from backend.app.config import (
    TELEGRAM_ALLOWED_USER_IDS,
    TELEGRAM_APPROVAL_CHAT_ID,
    TELEGRAM_APPROVAL_THREAD_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CALLBACK_AUDIT_DB_PATH,
    TELEGRAM_SEND_ENABLED,
)
from backend.app.telegram_callback_audit import DEFAULT_INITIAL_CASE_STATE, TelegramCallbackAuditStore
from backend.app.telegram_preview import APPROVAL_ACTIONS

CALLBACK_PREFIX = "disputepilot"
SUPPORTED_CALLBACK_ACTIONS = set(APPROVAL_ACTIONS.values())


class TelegramLoopError(RuntimeError):
    """Raised for Telegram loop and callback handling failures."""


class TelegramLoopDisabledError(TelegramLoopError):
    """Raised when outbound Telegram actions are disabled by config."""


class TelegramLoopConfigError(TelegramLoopError):
    """Raised when Telegram configuration is incomplete for sending."""


class TelegramLoopAuthorizationError(TelegramLoopError):
    """Raised when a Telegram sender is not permitted to act."""


def _telegram_api_base() -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _as_int(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _coerce_chat_id(chat_id: str) -> int | str:
    return _as_int(chat_id) or chat_id


def _require_allowed_sender_ids() -> set[int]:
    if TELEGRAM_ALLOWED_USER_IDS is None:
        raise TelegramLoopConfigError("DISPUTEPILOT_TELEGRAM_ALLOWED_USER_IDS must be configured before Telegram callbacks are accepted.")
    if not TELEGRAM_ALLOWED_USER_IDS:
        raise TelegramLoopConfigError("DISPUTEPILOT_TELEGRAM_ALLOWED_USER_IDS cannot be empty for Telegram callbacks.")
    return set(TELEGRAM_ALLOWED_USER_IDS)


def _message_text(case: dict[str, Any]) -> str:
    deadline = None
    if case.get("extracted_deadlines"):
        deadline = case["extracted_deadlines"][0].get("date")

    body = [
        f"{case['case_id']}: {case['case_type']}",
        f"Priority: {case.get('priority', 'unknown')}",
        f"Stage: {case.get('current_stage', 'unknown')}",
        f"Next action: {case.get('recommended_next_action', 'Review manually')}",
    ]
    if deadline:
        body.append(f"Deadline: {deadline}")

    return "\n".join(body)


def build_callback_payload(case_id: str, action: str) -> str:
    return f"{CALLBACK_PREFIX}:{case_id}:{action}"


def build_telegram_approval_payload(case: dict[str, Any]) -> dict[str, Any]:
    approval_markup = {
        "inline_keyboard": [
            [
                {
                    "text": label,
                    "callback_data": build_callback_payload(case["case_id"], action),
                }
                for label, action in APPROVAL_ACTIONS.items()
            ]
        ]
    }

    payload: dict[str, Any] = {
        "chat_id": _coerce_chat_id(TELEGRAM_APPROVAL_CHAT_ID),
        "text": _message_text(case),
        "reply_markup": approval_markup,
    }

    if TELEGRAM_APPROVAL_THREAD_ID:
        payload["message_thread_id"] = _coerce_chat_id(TELEGRAM_APPROVAL_THREAD_ID)

    return payload


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=encoded, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=5) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise TelegramLoopError("Unexpected Telegram response format.")
        return parsed


def send_case_for_telegram_approval(case: dict[str, Any]) -> dict[str, Any]:
    if not TELEGRAM_SEND_ENABLED:
        raise TelegramLoopDisabledError("Telegram send disabled. Set DISPUTEPILOT_TELEGRAM_SEND_ENABLED=true.")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_APPROVAL_CHAT_ID:
        raise TelegramLoopConfigError("TELEGRAM_BOT_TOKEN and TELEGRAM_APPROVAL_CHAT_ID are required to send approvals.")

    payload = build_telegram_approval_payload(case)
    try:
        result = _post_json(f"{_telegram_api_base()}/sendMessage", payload)
    except error.HTTPError as exc:
        raise TelegramLoopError(f"Telegram API returned HTTP {exc.code}.") from exc
    except error.URLError as exc:
        raise TelegramLoopError(f"Telegram API request failed: {exc.reason}") from exc

    message_id = None
    if isinstance(result.get("result"), dict):
        message_id = result["result"].get("message_id")

    return {
        "status": "telegram_approval_dispatched",
        "message_id": message_id,
        "chat_id": TELEGRAM_APPROVAL_CHAT_ID,
        "thread_id": TELEGRAM_APPROVAL_THREAD_ID or None,
        "telegram_response": result,
    }


def parse_telegram_update(payload: dict[str, Any]) -> dict[str, Any]:
    callback_query = payload.get("callback_query")
    if not isinstance(callback_query, dict):
        raise TelegramLoopError("Expected a callback_query payload.")

    callback_query_id = callback_query.get("id")
    if not isinstance(callback_query_id, str) or not callback_query_id.strip():
        raise TelegramLoopError("Missing callback query ID.")

    data = callback_query.get("data")
    if not isinstance(data, str):
        raise TelegramLoopError("Missing callback data.")

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
        raise TelegramLoopError("Unsupported callback payload format.")

    _, case_id, action = parts
    if action not in SUPPORTED_CALLBACK_ACTIONS:
        raise TelegramLoopError(f"Unsupported action '{action}'.")

    sender = callback_query.get("from")
    sender_id = sender.get("id") if isinstance(sender, dict) else None
    if not isinstance(sender_id, int):
        raise TelegramLoopError("Missing sender ID in callback payload.")

    allowed_sender_ids = _require_allowed_sender_ids()
    if sender_id not in allowed_sender_ids:
        raise TelegramLoopAuthorizationError("Sender is not authorized for this Telegram bot.")

    return {
        "case_id": case_id,
        "action": action,
        "callback_query_id": callback_query_id,
        "authorized_sender_id": sender_id,
    }


def get_telegram_callback_audit_store() -> TelegramCallbackAuditStore:
    return TelegramCallbackAuditStore(TELEGRAM_CALLBACK_AUDIT_DB_PATH)


def build_callback_audit_response(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "telegram_callback_duplicate_ignored" if record.get("duplicate") else "telegram_callback_recorded",
        "duplicate": bool(record.get("duplicate", False)),
        "audit_entry": {
            "case_id": record["case_id"],
            "action": record["action"],
            "callback_query_id": record["callback_query_id"],
            "authorized_sender_id": record["authorized_sender_id"],
            "timestamp": record["timestamp"],
            "previous_case_state": record["previous_case_state"],
            "resulting_case_state": record["resulting_case_state"],
            "idempotency_key": record["idempotency_key"],
        },
    }


def current_case_state_or_default(store: TelegramCallbackAuditStore, case_id: str) -> str:
    return store.get_current_case_state(case_id) or DEFAULT_INITIAL_CASE_STATE
