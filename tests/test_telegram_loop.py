from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_telegram_notify_endpoint_returns_preview_when_disabled():
    response = client.post("/cases/DP-DEBT-001/telegram/notify")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "telegram_send_disabled"
    assert payload["telegram_approval_preview"]["preview_only"] is True
    assert payload["telegram_approval_preview"]["send_enabled"] is False


def test_telegram_notify_endpoint_sends_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.get_integrations",
        lambda: {"gmail": False, "uipath": False, "telegram_send": True},
    )
    monkeypatch.setattr(
        "backend.app.main.send_case_for_telegram_approval",
        lambda case: {
            "status": "telegram_approval_dispatched",
            "message_id": 123,
            "chat_id": "-100123",
            "thread_id": None,
            "telegram_response": {"ok": True},
        },
    )

    response = client.post("/cases/DP-GAM-001/telegram/notify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "telegram_approval_dispatched"
    assert payload["message_id"] == 123
    assert payload["telegram_response"]["ok"] is True


def test_telegram_update_rejects_bad_payload():
    response = client.post("/telegram/updates", json={"message": {"text": "ignore"}})

    assert response.status_code == 400
    assert "Expected a callback_query payload" in response.json()["detail"]


def test_telegram_update_parses_valid_callback():
    callback_payload = {
        "callback_query": {
            "id": "cb-1",
            "from": {"id": 123456},
            "data": "disputepilot:DP-DEBT-001:approve_draft",
        }
    }
    response = client.post("/telegram/updates", json=callback_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "DP-DEBT-001"
    assert payload["action"] == "approve_draft"
    assert payload["callback_query_id"] == "cb-1"


def test_telegram_update_blocks_unallowlisted_sender(monkeypatch):
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", {987654}, raising=False)

    callback_payload = {
        "callback_query": {
            "id": "cb-2",
            "from": {"id": 123456},
            "data": "disputepilot:DP-DEBT-001:approve_draft",
        }
    }
    response = client.post("/telegram/updates", json=callback_payload)

    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]
