from __future__ import annotations

from typing import Any

from backend.app.config import UIPATH_INTEGRATION_ENABLED

ORCHESTRATION_LAYER = "UiPath Automation Cloud / Maestro Case"
WORKFLOW_STEPS = [
    "classify demo message",
    "create UiPath case",
    "extract deadline and risk",
    "draft reply for human review",
    "await Telegram approval",
    "log the outcome",
]


def _first_deadline(case: dict[str, Any]) -> str | None:
    deadlines = case.get("extracted_deadlines") or []
    if not deadlines:
        return None
    return deadlines[0].get("date")


def build_workflow_handoff_preview(case: dict[str, Any]) -> dict[str, Any]:
    deadline = _first_deadline(case)
    return {
        "preview_only": True,
        "orchestration_layer": ORCHESTRATION_LAYER,
        "integration_enabled": UIPATH_INTEGRATION_ENABLED,
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "case_title": f"{case['case_id']} - {case['case_type'].replace('_', ' ').title()}",
        "current_stage": case.get("current_stage", "unknown"),
        "uipath_case_stage": case.get("uipath_case_stage") or case.get("current_stage", "unknown"),
        "priority": case.get("priority", "medium"),
        "deadline": deadline,
        "approval_options": ["Approve", "Edit", "Snooze", "Mark done"],
        "workflow_steps": WORKFLOW_STEPS,
        "next_action": case.get("recommended_next_action", "Review synthetic case."),
        "summary": case.get("trigger_email_summary", "Synthetic demo case for handoff preview."),
    }
