from backend.app.fixture_loader import load_case
from backend.app.pipeline import analyze_case
from backend.app.redaction import scan_fixture_text
from backend.app.telegram_preview import APPROVAL_BUTTONS, build_telegram_card_preview
from backend.app.uipath_preview import build_uipath_case_payload_preview


def test_pipeline_normalizes_case_intelligence_output():
    raw = load_case("DP-DEBT-001")
    analysis = analyze_case(raw)

    expected_keys = {
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
        "telegram_card_preview",
        "uipath_case_payload_preview",
        "redaction_scan",
    }
    assert expected_keys.issubset(analysis.keys())
    assert analysis["case_id"] == "DP-DEBT-001"
    assert analysis["telegram_card_preview"]["buttons"] == APPROVAL_BUTTONS
    assert analysis["uipath_case_payload_preview"]["case_type"] == raw["case_type"]


def test_telegram_preview_is_plain_preview_and_does_not_send():
    card = build_telegram_card_preview(load_case("DP-GAM-002"))

    assert card["preview_only"] is True
    assert card["send_enabled"] is False
    assert "Request Evidence" in card["buttons"]


def test_uipath_preview_is_payload_preview_and_does_not_call_api():
    payload = build_uipath_case_payload_preview(load_case("DP-INS-001"))

    assert payload["preview_only"] is True
    assert payload["integration_enabled"] is False
    assert payload["case_title"].startswith("DP-INS-001")
    assert "evidence_gaps" in payload


def test_redaction_scanner_flags_sensitive_patterns_without_values():
    # Build risky-looking strings dynamically so the repository does not contain
    # static private-data-like fixtures while still testing the scanner.
    email_like = "demo" + "@" + "example" + ".test"
    phone_like = "+27 " + "82 " + "123 " + "4567"
    token_like = "sk-" + "abc12345"
    long_digit_like = "1234" + "567890"
    warnings = scan_fixture_text(f"Contact {email_like} or {phone_like} with token {token_like} and account {long_digit_like}")
    warning_types = {warning["type"] for warning in warnings}

    assert {"email_like", "phone_like", "long_digit_like", "secret_token_like"}.issubset(warning_types)
    assert all("demo@example" not in warning["message"] for warning in warnings)
    assert all("sk-" not in warning["message"] for warning in warnings)


def test_synthetic_fixtures_pass_redaction_scanner():
    for case_id in ["DP-DEBT-001", "DP-INS-001", "DP-GAM-001", "DP-GAM-002", "DP-SVC-001", "DP-CREDIT-001"]:
        analysis = analyze_case(load_case(case_id))
        assert analysis["redaction_scan"]["warning_count"] == 0
