from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from backend.app.config import APP_NAME, DEFAULT_FIXTURE_DIR, DEMO_MODE, get_integrations
from backend.app.fixture_loader import CaseNotFoundError, FixtureLoadError, load_case, load_cases
from backend.app.models import HealthResponse
from backend.app.pipeline import analyze_case
from backend.app.telegram_approval import build_telegram_approval_preview
from backend.app.telegram_callback_audit import TelegramCallbackStaleCardError, TelegramCallbackTransitionError
from backend.app.telegram_loop import (
    TelegramLoopAuthorizationError,
    TelegramLoopConfigError,
    TelegramLoopDisabledError,
    TelegramLoopError,
    TelegramLoopStaleCardError,
    build_callback_audit_response,
    build_stale_card_response,
    current_case_state_or_default,
    get_telegram_callback_audit_store,
    invalidate_telegram_callback_keyboard,
    parse_telegram_update,
    send_case_for_telegram_approval,
)
from backend.app.uipath_integration import (
    UiPathIntegrationError,
    UiPathNotConfiguredError,
    build_uipath_handoff_payload,
    send_case_to_uipath,
)
from backend.app.workflow_preview import build_workflow_handoff_preview

app = FastAPI(
    title="DisputePilot API",
    description="Synthetic FastAPI skeleton for DisputePilot dispute intelligence demos.",
    version="0.1.0",
)


def _fixture_dir() -> Path:
    return Path(getattr(app.state, "fixture_dir", DEFAULT_FIXTURE_DIR))


def _case_not_found(exc: CaseNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _fixture_failure(exc: FixtureLoadError) -> HTTPException:
    return HTTPException(status_code=500, detail=str(exc))


def _current_integrations() -> dict[str, bool]:
    return get_integrations()


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, object]:
    return {"status": "ok", "demo_mode": DEMO_MODE, "app": APP_NAME, "integrations": _current_integrations()}


@app.get("/cases")
def list_cases() -> dict[str, object]:
    try:
        cases = load_cases(_fixture_dir())
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc
    return {
        "demo_mode": DEMO_MODE,
        "count": len(cases),
        "cases": [
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "priority": case["priority"],
                "current_stage": case["current_stage"],
                "fake_company": case["fake_company"],
                "source_label": case["source_label"],
            }
            for case in cases
        ],
    }


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, object]:
    try:
        return load_case(case_id, _fixture_dir())
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc


@app.post("/cases/{case_id}/analyze")
def analyze_case_endpoint(case_id: str) -> dict[str, object]:
    try:
        return analyze_case(load_case(case_id, _fixture_dir()))
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc


@app.post("/cases/{case_id}/handoff", response_model=None)
def handoff_case_endpoint(case_id: str) -> object:
    try:
        case = load_case(case_id, _fixture_dir())
        if not _current_integrations().get("uipath", False):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "uipath_integration_disabled",
                    "message": "Set UIPATH_INTEGRATION_ENABLED=true and UIPATH_WEBHOOK_URL to enable live handoff.",
                    "workflow_handoff_preview": build_workflow_handoff_preview(case),
                    "uipath_payload_preview": build_uipath_handoff_payload(case),
                },
            )

        return send_case_to_uipath(case)
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc
    except UiPathNotConfiguredError as exc:
        return JSONResponse(status_code=503, content={"status": "uipath_integration_config_missing", "message": str(exc)})
    except UiPathIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc


@app.post("/cases/{case_id}/telegram/notify", response_model=None)
def telegram_notify_case_endpoint(case_id: str) -> object:
    try:
        case = load_case(case_id, _fixture_dir())
        store = get_telegram_callback_audit_store()
        case_state = store.get_case_state(case_id)
        preview = build_telegram_approval_preview(
            case,
            case_state=case_state["current_case_state"],
            card_revision=case_state["active_revision"],
        )
        if not _current_integrations().get("telegram_send", False):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "telegram_send_disabled",
                    "message": "Set DISPUTEPILOT_TELEGRAM_SEND_ENABLED=true and bot credentials to enable live Telegram send.",
                    "telegram_approval_preview": preview,
                },
            )

        return send_case_for_telegram_approval(
            case,
            case_state=case_state["current_case_state"],
            card_revision=case_state["active_revision"],
        )
    except TelegramLoopDisabledError as exc:
        return JSONResponse(status_code=503, content={"status": "telegram_send_disabled", "message": str(exc)})
    except TelegramLoopConfigError as exc:
        return JSONResponse(status_code=503, content={"status": "telegram_integration_not_configured", "message": str(exc)})
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc


@app.post("/telegram/updates", response_model=None)
def telegram_callback_updates(update: dict[str, Any]) -> object:
    parsed: dict[str, Any] = {}
    try:
        parsed = parse_telegram_update(update)
        case = load_case(parsed["case_id"], _fixture_dir())
        store = get_telegram_callback_audit_store()
        record = store.record_callback(
            case_id=parsed["case_id"],
            action=parsed["action"],
            callback_query_id=parsed["callback_query_id"],
            authorized_sender_id=parsed["authorized_sender_id"],
            callback_revision=parsed["callback_revision"],
        )
        keyboard_invalidation = None
        try:
            keyboard_invalidation = invalidate_telegram_callback_keyboard(parsed)
        except TelegramLoopError:
            keyboard_invalidation = {"status": "failed", "reason": "keyboard_invalidation_failed"}
        return {
            **build_callback_audit_response(record, keyboard_invalidation=keyboard_invalidation),
            "case_exists": True,
            "synthetic_case_summary": {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "current_stage": case.get("current_stage"),
                "priority": case.get("priority"),
            },
        }
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc
    except TelegramLoopAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TelegramLoopConfigError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TelegramLoopStaleCardError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TelegramCallbackStaleCardError as exc:
        store = get_telegram_callback_audit_store()
        return JSONResponse(
            status_code=409,
            content=build_stale_card_response(
                case_id=parsed["case_id"],
                callback_revision=parsed.get("callback_revision"),
                case_state=store.get_case_state(parsed["case_id"]),
            ),
        )
    except TelegramLoopError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/cases/{case_id}/telegram/audit-history")
def telegram_callback_audit_history(case_id: str) -> dict[str, Any]:
    try:
        case = load_case(case_id, _fixture_dir())
        store = get_telegram_callback_audit_store()
        history = store.get_public_case_history(case_id)
        current_state = store.get_current_case_state(case_id) or current_case_state_or_default(store, case_id)
        return {
            "case_id": case_id,
            "case_exists": True,
            "current_case_state": current_state,
            "history_count": len(history),
            "history": history,
            "case_summary": {
                "case_type": case["case_type"],
                "current_stage": case.get("current_stage"),
                "priority": case.get("priority"),
            },
        }
    except CaseNotFoundError as exc:
        raise _case_not_found(exc) from exc


@app.get("/demo")
def demo_summary() -> dict[str, object]:
    try:
        cases = load_cases(_fixture_dir())
    except FixtureLoadError as exc:
        raise _fixture_failure(exc) from exc
    analyses = [analyze_case(case) for case in cases]
    return {
        "demo_mode": DEMO_MODE,
        "case_count": len(analyses),
        "integrations": _current_integrations(),
        "cases": [
            {
                "case_id": item["case_id"],
                "case_type": item["case_type"],
                "priority": item["priority"],
                "current_stage": item["current_stage"],
                "next_action": item["recommended_next_action"],
                "deadline": (item["extracted_deadlines"][0].get("date") if item["extracted_deadlines"] else None),
            }
            for item in analyses
        ],
    }
