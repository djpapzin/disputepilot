from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import DEFAULT_FIXTURE_DIR

REQUIRED_FIELDS: set[str] = {
    "case_id",
    "case_type",
    "fake_company",
    "fake_sender",
    "source_label",
    "priority",
    "current_stage",
    "trigger_email_summary",
    "timeline_events",
    "extracted_deadlines",
    "disputed_amounts",
    "evidence_matrix",
    "missing_evidence",
    "company_response_gaps",
    "recommended_next_action",
    "draft_reply_outline",
    "telegram_card_preview",
    "uipath_case_stage",
    "redaction_required",
}


class FixtureLoadError(RuntimeError):
    """Raised when synthetic demo fixtures cannot be loaded safely."""


class CaseNotFoundError(FixtureLoadError):
    """Raised when fixture data loads safely but the requested synthetic case is absent."""


def _validate_fixture(data: dict[str, Any], source: Path) -> dict[str, Any]:
    missing = sorted(REQUIRED_FIELDS.difference(data))
    if missing:
        raise FixtureLoadError(f"Fixture {source.name} missing required fields: {', '.join(missing)}")
    return data


def load_cases(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> list[dict[str, Any]]:
    """Load all synthetic case JSON fixtures.

    This loader never reaches out to Gmail, UiPath, Telegram, or any live service.
    """

    folder = Path(fixture_dir)
    if not folder.exists() or not folder.is_dir():
        raise FixtureLoadError(f"Fixture folder not found: {folder}")

    cases: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FixtureLoadError(f"Invalid JSON fixture: {path.name}") from exc
        if not isinstance(parsed, dict):
            raise FixtureLoadError(f"Fixture {path.name} must contain a JSON object")
        cases.append(_validate_fixture(parsed, path))

    return cases


def load_case(case_id: str, fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    for case in load_cases(fixture_dir):
        if case["case_id"] == case_id:
            return case
    raise CaseNotFoundError(f"Synthetic case not found: {case_id}")
