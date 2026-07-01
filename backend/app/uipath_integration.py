from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.config import (
    UIPATH_AUTH_TOKEN,
    UIPATH_INTEGRATION_ENABLED,
    UIPATH_QUEUE_NAME,
    UIPATH_TENANT_URL,
    UIPATH_WEBHOOK_URL,
)


class UiPathIntegrationError(RuntimeError):
    """Raised when UiPath handoff cannot be performed."""


class UiPathNotConfiguredError(UiPathIntegrationError):
    """Raised when required UiPath settings are missing."""


def build_uipath_handoff_payload(case: dict[str, Any]) -> dict[str, Any]:
    """Build the payload submitted to UiPath Maestro Case.

    The payload uses synthetic-safe fields and maps directly from case intelligence.
    """

    return {
        "source": "DisputePilot",
        "source_case_id": case["case_id"],
        "case_type": case["case_type"],
        "priority": case.get("priority", "medium"),
        "current_stage": case.get("uipath_case_stage") or case.get("current_stage", "unknown"),
        "summary": case.get("trigger_email_summary", "Synthetic case handoff."),
        "deadline": _first_deadline(case),
        "missing_evidence": list(case.get("missing_evidence", [])),
        "recommended_next_action": case.get("recommended_next_action", "Review synthetic case."),
        "redaction_required": bool(case.get("redaction_required", False)),
        "queue_name": UIPATH_QUEUE_NAME,
        "tenant_url": UIPATH_TENANT_URL,
        "workflow": {
            "orchestration_layer": "UiPath Automation Cloud / Maestro Case",
            "workflow_stage": case.get("uipath_case_stage") or case.get("current_stage", "unknown"),
            "approval_state": "PendingHumanReview",
        },
    }


def _first_deadline(case: dict[str, Any]) -> str | None:
    deadlines = case.get("extracted_deadlines") or []
    if not deadlines:
        return None
    return deadlines[0].get("date")


def _request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if UIPATH_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {UIPATH_AUTH_TOKEN}"
    return headers


def _ensure_integration_ready() -> None:
    if not UIPATH_INTEGRATION_ENABLED:
        raise UiPathNotConfiguredError("UiPath integration is disabled")

    if not UIPATH_WEBHOOK_URL:
        raise UiPathNotConfiguredError("UIPATH_WEBHOOK_URL is not configured")


def send_case_to_uipath(case: dict[str, Any]) -> dict[str, Any]:
    """Send the handoff payload to UiPath.

    This implementation uses an outbound webhook-style handoff to keep the
    integration lightweight and testable in a synthetic project.
    """

    _ensure_integration_ready()
    payload = build_uipath_handoff_payload(case)

    request = Request(
        UIPATH_WEBHOOK_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_request_headers(),
        method="POST",
    )

    try:
        with urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8") if response else ""
            if response.getcode() >= 400:
                raise UiPathIntegrationError(f"UiPath returned HTTP {response.getcode()}: {raw or 'empty body'}")
            parsed: dict[str, Any]
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw_response": raw}
            parsed.update({"status": "ok", "payload": payload, "http_status": response.getcode()})
            return parsed
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        raise UiPathIntegrationError(f"UiPath API returned {exc.code}: {body or 'no response body'}") from exc
    except URLError as exc:
        raise UiPathIntegrationError(f"Unable to contact UiPath endpoint: {exc}") from exc
