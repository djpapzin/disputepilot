from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["demo_mode"] is True


def test_cases_lists_synthetic_cases():
    response = client.get("/cases")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 6
    assert payload["demo_mode"] is True
    assert {case["case_id"] for case in payload["cases"]} >= {"DP-DEBT-001", "DP-SVC-001"}


def test_case_detail_returns_raw_synthetic_fixture():
    response = client.get("/cases/DP-CREDIT-001")

    assert response.status_code == 200
    assert response.json()["case_id"] == "DP-CREDIT-001"


def test_unknown_case_returns_404():
    response = client.get("/cases/DP-NOPE-999")

    assert response.status_code == 404


def test_analyze_case_endpoint():
    response = client.post("/cases/DP-GAM-001/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "DP-GAM-001"
    assert payload["telegram_card_preview"]["preview_only"] is True
    assert payload["uipath_case_payload_preview"]["preview_only"] is True


def test_demo_endpoint_returns_compact_summary():
    response = client.get("/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["demo_mode"] is True
    assert payload["case_count"] == 6
    assert all("case_id" in case for case in payload["cases"])


def test_no_real_integration_routes_or_flags_enabled():
    health = client.get("/health").json()
    analysis = client.post("/cases/DP-DEBT-001/analyze").json()

    assert health["integrations"] == {"gmail": False, "uipath": False, "telegram_send": False}
    assert analysis["telegram_card_preview"]["send_enabled"] is False
    assert analysis["uipath_case_payload_preview"]["integration_enabled"] is False
