from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from backend.app.config import APP_NAME, DEFAULT_FIXTURE_DIR, DEMO_MODE, get_integrations
from backend.app.fixture_loader import CaseNotFoundError, FixtureLoadError, load_case, load_cases
from backend.app.models import HealthResponse
from backend.app.pipeline import analyze_case
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
