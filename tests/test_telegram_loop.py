from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.telegram_callback_audit import TelegramCallbackAuditStore, TelegramCallbackTransitionError

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
def allowlist_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", None, raising=False)


@pytest.fixture()
def allowlist_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", set(), raising=False)


@pytest.fixture()
def allow_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", {123456}, raising=False)


@pytest.fixture()
def deny_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.telegram_loop.TELEGRAM_ALLOWED_USER_IDS", {987654}, raising=False)


@pytest.mark.parametrize(
    ("label", "action", "expected_state"),
    [
        ("Approve", "approve_draft", "approved_draft"),
        ("Edit", "edit_draft", "edit_requested"),
        ("Snooze", "snooze_draft", "snoozed"),
        ("Mark done", "mark_done", "completed"),
    ],
)
def test_telegram_callback_persists_supported_actions(audit_db: Path, allow_sender: None, label: str, action: str, expected_state: str):
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
    assert history_payload["history"][0] == {
        "action": action,
        "previous_case_state": "draft_pending",
        "resulting_case_state": expected_state,
    }
    assert "authorized_sender_id" not in json.dumps(history_payload)
    assert "callback_query_id" not in json.dumps(history_payload)
    assert "timestamp" not in json.dumps(history_payload)


@pytest.mark.parametrize(
    ("allowlist_fixture", "expected_detail"),
    [
        ("allowlist_none", "must be configured"),
        ("allowlist_empty", "cannot be empty"),
    ],
)
def test_telegram_callback_rejects_missing_or_empty_allowlist(audit_db: Path, request: pytest.FixtureRequest, allowlist_fixture: str, expected_detail: str):
    request.getfixturevalue(allowlist_fixture)

    response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": f"cb-{allowlist_fixture}",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:approve_draft",
            }
        },
    )

    assert response.status_code == 403
    assert expected_detail in response.json()["detail"]
    assert client.get("/cases/DP-DEBT-001/telegram/audit-history").json()["history_count"] == 0


def test_telegram_callback_rejects_unauthorized_sender(audit_db: Path, deny_sender: None):
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
def test_telegram_callback_rejects_malformed_payloads(audit_db: Path, allow_sender: None, payload: dict[str, object]):
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
                "data": "disputepilot:DP-DEBT-001:edit_draft",
            }
        },
    )

    assert invalid_transition.status_code == 409
    assert "Unsupported transition" in invalid_transition.json()["detail"]
    history = client.get("/cases/DP-DEBT-001/telegram/audit-history").json()
    assert history["history_count"] == 1
    assert history["current_case_state"] == "approved_draft"


@pytest.mark.parametrize(
    "start_action",
    ["edit_draft", "snooze_draft"],
)
def test_telegram_callback_approval_can_follow_deferred_states(audit_db: Path, allow_sender: None, start_action: str):
    first = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": f"cb-deferred-{start_action}-1",
                "from": {"id": 123456},
                "data": f"disputepilot:DP-DEBT-001:{start_action}",
            }
        },
    )
    assert first.status_code == 200
    assert first.json()["audit_entry"]["resulting_case_state"] in {"edit_requested", "snoozed"}

    second = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": f"cb-deferred-{start_action}-2",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:approve_draft",
            }
        },
    )
    assert second.status_code == 200
    assert second.json()["audit_entry"]["previous_case_state"] in {"edit_requested", "snoozed"}
    assert second.json()["audit_entry"]["resulting_case_state"] == "approved_draft"

    history = client.get("/cases/DP-DEBT-001/telegram/audit-history").json()
    assert history["history_count"] == 2
    assert history["current_case_state"] == "approved_draft"


def test_telegram_callback_concurrent_requests_are_serialized(audit_db: Path, allow_sender: None):
    barrier = Barrier(2)

    def submit(action: str, callback_id: str):
        barrier.wait()
        store = TelegramCallbackAuditStore(audit_db)
        return store.record_callback(
            case_id="DP-DEBT-001",
            action=action,
            callback_query_id=callback_id,
            authorized_sender_id=123456,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(submit, "approve_draft", "cb-concurrent-1"),
            executor.submit(submit, "approve_draft", "cb-concurrent-2"),
        ]
        results = []
        errors = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - captured for assertion
                errors.append(exc)

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], TelegramCallbackTransitionError)
    history = TelegramCallbackAuditStore(audit_db).get_case_history("DP-DEBT-001")
    assert len(history) == 1
    assert history[0]["resulting_case_state"] == "approved_draft"
    assert TelegramCallbackAuditStore(audit_db).get_current_case_state("DP-DEBT-001") == "approved_draft"


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


def test_telegram_callback_persistence_survives_new_store_instance(audit_db: Path, allow_sender: None):
    response = client.post(
        "/telegram/updates",
        json={
            "callback_query": {
                "id": "cb-restart-safe",
                "from": {"id": 123456},
                "data": "disputepilot:DP-DEBT-001:mark_done",
            }
        },
    )

    assert response.status_code == 200

    fresh_store = TelegramCallbackAuditStore(audit_db)
    history = fresh_store.get_case_history("DP-DEBT-001")
    assert len(history) == 1
    assert history[0]["callback_query_id"] == "cb-restart-safe"
    assert history[0]["resulting_case_state"] == "completed"
    assert fresh_store.get_current_case_state("DP-DEBT-001") == "completed"
