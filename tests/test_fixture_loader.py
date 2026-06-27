import json
from pathlib import Path

import pytest

from backend.app.fixture_loader import REQUIRED_FIELDS, CaseNotFoundError, FixtureLoadError, load_case, load_cases


def test_load_cases_returns_all_synthetic_fixtures():
    cases = load_cases()

    assert len(cases) == 6
    assert {case["case_id"] for case in cases} >= {"DP-DEBT-001", "DP-INS-001", "DP-GAM-001"}


def test_loaded_cases_have_required_fields():
    for case in load_cases():
        assert REQUIRED_FIELDS.issubset(case.keys())
        assert case["redaction_required"]["required"] is True


def test_load_case_returns_specific_case():
    case = load_case("DP-SVC-001")

    assert case["case_id"] == "DP-SVC-001"
    assert case["case_type"] == "service_delivery_billing_dispute"


def test_load_case_unknown_raises_safe_error():
    with pytest.raises(CaseNotFoundError, match="Synthetic case not found"):
        load_case("DP-NOPE-999")


def test_missing_fixture_folder_fails_safely(tmp_path: Path):
    with pytest.raises(FixtureLoadError, match="Fixture folder not found"):
        load_cases(tmp_path / "missing")


def test_invalid_json_fails_safely(tmp_path: Path):
    folder = tmp_path / "cases"
    folder.mkdir()
    (folder / "bad.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(FixtureLoadError, match="Invalid JSON fixture"):
        load_cases(folder)


def test_missing_required_field_fails_safely(tmp_path: Path):
    folder = tmp_path / "cases"
    folder.mkdir()
    fixture = {field: "demo" for field in REQUIRED_FIELDS}
    fixture.pop("case_id")
    (folder / "missing.json").write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(FixtureLoadError, match="missing required fields"):
        load_cases(folder)
