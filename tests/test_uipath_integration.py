from fastapi.testclient import TestClient

from backend.app.fixture_loader import load_case
from backend.app.main import app
from backend.app.uipath_integration import build_uipath_handoff_payload

client = TestClient(app)


def test_handoff_endpoint_returns_preview_when_integration_disabled():
    response = client.post("/cases/DP-DEBT-001/handoff")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "uipath_integration_disabled"
    assert payload["workflow_handoff_preview"]["preview_only"] is True
    assert payload["workflow_handoff_preview"]["integration_enabled"] is False
    assert payload["uipath_payload_preview"]["source_case_id"] == "DP-DEBT-001"


def test_uipath_handoff_payload_includes_maestro_fields():
    payload = build_uipath_handoff_payload(load_case("DP-INS-001"))

    assert payload["source_case_id"].startswith("DP-INS-001")
    assert payload["workflow"]["orchestration_layer"] == "UiPath Automation Cloud / Maestro Case"
    assert payload["workflow"]["approval_state"] == "PendingHumanReview"


def test_handoff_endpoint_calls_integration_when_enabled(monkeypatch):
    monkeypatch.setattr("backend.app.main.get_integrations", lambda: {"gmail": False, "uipath": True, "telegram_send": False})
    monkeypatch.setattr("backend.app.main.send_case_to_uipath", lambda case: {
        "status": "ok",
        "uipath_reference": "uipath-case-001",
        "payload": build_uipath_handoff_payload(case),
    })

    response = client.post("/cases/DP-GAM-001/handoff")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["uipath_reference"] == "uipath-case-001"
    assert payload["payload"]["source_case_id"] == "DP-GAM-001"
