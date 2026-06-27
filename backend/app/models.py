from typing import Any, Literal

from pydantic import BaseModel, Field


class RedactionWarning(BaseModel):
    type: str
    message: str


class CaseListItem(BaseModel):
    case_id: str
    case_type: str
    priority: str
    current_stage: str
    fake_company: str
    source_label: str


class TelegramCardPreview(BaseModel):
    preview_only: bool = True
    send_enabled: bool = False
    title: str
    body: str
    buttons: list[str]


class UiPathCasePayloadPreview(BaseModel):
    preview_only: bool = True
    integration_enabled: bool = False
    case_title: str
    case_type: str
    stage: str
    priority: str
    deadline: str | None = None
    evidence_gaps: list[str] = Field(default_factory=list)
    recommended_next_action: str


class RedactionScanResult(BaseModel):
    warning_count: int
    warnings: list[RedactionWarning]


class CaseIntelligence(BaseModel):
    case_id: str
    case_type: str
    priority: str
    current_stage: str
    timeline_events: list[dict[str, Any]]
    extracted_deadlines: list[dict[str, Any]]
    disputed_amounts: list[dict[str, Any]]
    evidence_matrix: list[dict[str, Any]]
    missing_evidence: list[str]
    company_response_gaps: list[str]
    recommended_next_action: str
    draft_reply_outline: list[str]
    redaction_required: dict[str, Any]
    telegram_card_preview: dict[str, Any]
    uipath_case_payload_preview: dict[str, Any]
    redaction_scan: dict[str, Any]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    demo_mode: bool
    app: str
    integrations: dict[str, bool]
