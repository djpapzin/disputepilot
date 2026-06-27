from __future__ import annotations

from fastapi import FastAPI, HTTPException

from backend.app.config import APP_NAME, DEMO_MODE, INTEGRATIONS
from backend.app.fixture_loader import FixtureLoadError, load_case, load_cases
from backend.app.models import HealthResponse
from backend.app.pipeline import analyze_case

app = FastAPI(
    title="DisputePilot API",
    description="Synthetic FastAPI skeleton for DisputePilot dispute intelligence demos. No real integrations are enabled.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, object]:
    return {"status": "ok", "demo_mode": DEMO_MODE, "app": APP_NAME, "integrations": INTEGRATIONS}


@app.get("/cases")
def list_cases() -> dict[str, object]:
    try:
        cases = load_cases()
    except FixtureLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
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
        return load_case(case_id)
    except FixtureLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/cases/{case_id}/analyze")
def analyze_case_endpoint(case_id: str) -> dict[str, object]:
    try:
        return analyze_case(load_case(case_id))
    except FixtureLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/demo")
def demo_summary() -> dict[str, object]:
    try:
        cases = load_cases()
    except FixtureLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    analyses = [analyze_case(case) for case in cases]
    return {
        "demo_mode": DEMO_MODE,
        "case_count": len(analyses),
        "integrations": INTEGRATIONS,
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
