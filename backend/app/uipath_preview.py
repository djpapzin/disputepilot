from __future__ import annotations

from typing import Any

from backend.app.config import UIPATH_INTEGRATION_ENABLED


def _first_deadline(case: dict[str, Any]) -> str | None:
    deadlines = case.get("extracted_deadlines") or []
    if not deadlines:
        return None
    return deadlines[0].get("date")


def build_uipath_case_payload_preview(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "preview_only": True,
        "integration_enabled": UIPATH_INTEGRATION_ENABLED,
        "case_title": f"{case['case_id']} - {case['case_type'].replace('_', ' ').title()}",
        "case_type": case["case_type"],
        "stage": case.get("uipath_case_stage") or case.get("current_stage"),
        "priority": case.get("priority", "medium"),
        "deadline": _first_deadline(case),
        "evidence_gaps": list(case.get("missing_evidence", [])),
        "recommended_next_action": case.get("recommended_next_action", "Review synthetic case."),
    }
