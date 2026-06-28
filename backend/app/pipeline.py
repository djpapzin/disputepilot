from __future__ import annotations

from typing import Any

from backend.app.redaction import scan_fixture
from backend.app.telegram_preview import build_telegram_card_preview
from backend.app.uipath_preview import build_uipath_case_payload_preview
from backend.app.workflow_preview import build_workflow_handoff_preview

PIPELINE_FIELDS = [
    "case_id",
    "case_type",
    "priority",
    "current_stage",
    "timeline_events",
    "extracted_deadlines",
    "disputed_amounts",
    "evidence_matrix",
    "missing_evidence",
    "company_response_gaps",
    "recommended_next_action",
    "draft_reply_outline",
    "redaction_required",
]


def analyze_case(case: dict[str, Any]) -> dict[str, Any]:
    """Produce placeholder case intelligence from a synthetic fixture."""

    normalized = {field: case[field] for field in PIPELINE_FIELDS}
    normalized["telegram_card_preview"] = build_telegram_card_preview(case)
    normalized["uipath_case_payload_preview"] = build_uipath_case_payload_preview(case)
    normalized["workflow_handoff_preview"] = build_workflow_handoff_preview(case)
    normalized["redaction_scan"] = scan_fixture(case)
    return normalized
