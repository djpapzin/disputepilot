from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.telegram_callback_audit import TelegramCallbackAuditStore

client = TestClient(app)


@pytest.fixture()
def audit_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "telegram_callback_audit.sqlite3"
    monkeypatch.setattr(
        "backend.app.main.get_telegram_callback_audit_store",
        lambda: TelegramCallbackAuditStore(db_path),
    )
    return db_path


@pytest.fixture()
def allow_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", {123456}, raising=False)


@pytest.fixture()
def allow_any_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", set(), raising=False)


@pytest.mark.parametrize(
    ("action", "expected_state"),
    [
        ("approve_draft", "approved_draft"),
        ("reject_draft", "rejected_draft"),
        ("escalate", "escalated"),
    ],
)
def test_telegram_callback_persists_supported_actions(audit_db: Path, allow_sender: None, action: str, expected_state: str):
    callback_payload = {
        "callback_query": {
            "id": f"cb-{action}",
            "from": {"id": 123456},
            "data": f"disputepilot:DP-DEBT-001:{action}",
        }
    }

    response = client.post("/telegram/updates", json=callback_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "telegram_callback_recorded"
    assert payload["duplicate"] is False
    assert payload["audit_entry"]["case_id"] == "DP-DEBT-001"
    assert payload["audit_entry"]["action"] == action
    assert payload["audit_entry"]["callback_query_id"] == f"cb-{action}"
    assert payload["audit_entry"]["authorized_sender_id"] == 123456
    assert payload["audit_entry"]["previous_case_state"] == "draft_pending"
    assert payload["audit_entry"]["resulting_case_state"] == expected_state
    assert len(payload["audit_entry"]["idempotency_key"]) == 64

    history = client.get("/cases/DP-DEBT-001/telegram/audit-history")
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["history_count"] == 1
    assert history_payload["current_case_state"] == expected_state
    assert history_payload["history"][0]["resulting_case_state"] == expected_state


def test_telegram_callback_duplicate_callback_id_is_idempotent(audit_db: Path, allow_sender: None):
    callback_payload = {
        "callback_query": {
            "id": "cb-duplicate",
            "from": {"id": 123456},
            "data": "disputepilot:DP-DEBT-001:approve_draft",
        }
    }

    first = client.post("/telegram/updates", json=callback_payload)
    second = client.post("/telegram/updates", json=callback_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["audit_entry"]["callback_query_id"] == "cb-duplicate"
    assert second.json()["audit_entry"]["resulting_case_state"] == "approved_draft"
    assert client.get("/cases/DP-DEBT-001/telegram/audit-history").json()["history_count"] == 1


def test_telegram_callback_rejects_unauthorized_sender(audit_db: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", {987654}, raising=False)

    response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": "cb-unauth",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:approve_draft",
            }
        },
    )

    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]
    assert client.get("/cases/DP-DEBT-001/telegram/audit-history").json()["history_count"] == 0


@pytest.mark.parametrize("case_id", ["DP-NOPE-999", "DP-UNKNOWN-404"])
def test_telegram_callback_rejects_unknown_case(audit_db: Path, allow_sender: None, case_id: str):
    response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": f"cb-{case_id}",
                "from": {"id": 123456},
                "data": f"disputepilot:{case_id}:approve_draft",
            }
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"message": {"text": "ignore"}},
        {"callback_query": {"id": "cb-bad", "from": {"id": 123456}, "data": "garbled-payload"}},
    ],
)
def test_telegram_callback_rejects_malformed_payloads(audit_db: Path, allow_any_sender: None, payload: dict[str, object]):
    response = client.post("/telegram/updates", json=payload)

    assert response.status_code == 400


def test_telegram_callback_rejects_invalid_state_transition(audit_db: Path, allow_sender: None):
    approve_response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": "cb-transition-1",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:approve_draft",
            }
        },
    )
    assert approve_response.status_code == 200

    invalid_transition = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": "cb-transition-2",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:reject_draft",
            }
        },
    )

    assert invalid_transition.status_code == 409
    assert "Unsupported transition" in invalid_transition.json()["detail"]
    history = client.get("/cases/DP-DEBT-001/telegram/audit-history").json()
    assert history["history_count"] == 1
    assert history["current_case_state"] == "approved_draft"


def test_telegram_callback_persistence_survives_new_store_instance(audit_db: Path, allow_sender: None):
    response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": "cb-restart-safe",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:escalate",
            }
        },
    )

    assert response.status_code == 200

    fresh_store = TelegramCallbackAuditStore(audit_db)
    history = fresh_store.get_case_history("DP-DEBT-001")
    assert len(history) == 1
    assert history[0]["callback_query_id"] == "cb-restart-safe"
    assert history[0]["resulting_case_state"] == "escalated"
    assert fresh_store.get_current_case_state("DP-DEBT-001") == "escalated"
