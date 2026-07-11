from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.telegram_approval import build_telegram_approval_preview
from backend.app.telegram_callback_audit import TelegramCallbackAuditStore, TelegramCallbackStaleCardError
from backend.app.telegram_loop import (
    TelegramLoopError,
    build_callback_audit_response,
    build_stateful_telegram_approval_payload,
)
from backend.app.telegram_preview import APPROVAL_ACTIONS_BY_STATE, approval_buttons_for_state

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


def _callback(action: str, revision: int, callback_id: str, case_id: str = "DP-DEBT-001") -> dict[str, object]:
    return {
        "callback_query": {
            "id": callback_id,
            "from": {"id": 123456},
            "data": f"disputepilot:{case_id}:{revision}:{action}",
            "message": {"message_id": 9001, "chat": {"id": -100123456}},
        }
    }


@pytest.mark.parametrize(
    ("label", "action", "expected_state"),
    [
        ("Approve", "approve_draft", "approved_draft"),
        ("Edit", "edit_draft", "edit_requested"),
        ("Snooze", "snooze_draft", "snoozed"),
        ("Mark done", "mark_done", "completed"),
    ],
)
def test_telegram_callback_persists_supported_actions(
    audit_db: Path, allow_sender: None, label: str, action: str, expected_state: str
):
    callback_payload = _callback(action=action, revision=1, callback_id=f"cb-{action}")

    response = client.post("/telegram/updates", json=callback_payload)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "telegram_callback_recorded"
    assert payload["duplicate"] is False
    assert payload["audit_entry"]["case_id"] == "DP-DEBT-001"
    assert payload["audit_entry"]["action"] == action
    assert payload["audit_entry"]["callback_query_id"] == f"cb-{action}"
    assert payload["audit_entry"]["callback_revision"] == 1
    assert payload["audit_entry"]["authorized_sender_id"] == 123456
    assert payload["audit_entry"]["previous_case_state"] == "draft_pending"
    assert payload["audit_entry"]["resulting_case_state"] == expected_state
    assert payload["audit_entry"]["active_revision_before"] == 1
    assert payload["audit_entry"]["active_revision_after"] == 2
    assert len(payload["audit_entry"]["idempotency_key"]) == 64
    assert payload["keyboard_invalidation"]["status"] in {"disabled", "skipped", "failed"}

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
def test_telegram_callback_rejects_missing_or_empty_allowlist(
    audit_db: Path, request: pytest.FixtureRequest, allowlist_fixture: str, expected_detail: str
):
    request.getfixturevalue(allowlist_fixture)

    response = client.post(
        "/telegram/updates",
        json=_callback(action="approve_draft", revision=1, callback_id=f"cb-{allowlist_fixture}"),
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
                "data": "disputepilot:DP-DEBT-001:1:approve_draft",
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
        json=_callback(action="approve_draft", revision=1, callback_id=f"cb-{case_id}", case_id=case_id),
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


def test_telegram_callback_rejects_old_approve_after_edit(audit_db: Path, allow_sender: None):
    edit_response = client.post("/telegram/updates", json=_callback("edit_draft", 1, "cb-edit-1"))
    assert edit_response.status_code == 200
    assert edit_response.json()["audit_entry"]["resulting_case_state"] == "edit_requested"

    stale_response = client.post("/telegram/updates", json=_callback("approve_draft", 1, "cb-approve-stale"))
    assert stale_response.status_code == 409
    stale_payload = stale_response.json()
    assert stale_payload["status"] == "telegram_callback_stale_card"
    assert stale_payload["stale_card"] is True
    assert stale_payload["active_revision"] == 2
    assert stale_payload["current_case_state"] == "edit_requested"

    fresh_response = client.post("/telegram/updates", json=_callback("approve_draft", 2, "cb-approve-fresh"))
    assert fresh_response.status_code == 200
    assert fresh_response.json()["audit_entry"]["previous_case_state"] == "edit_requested"
    assert fresh_response.json()["audit_entry"]["resulting_case_state"] == "approved_draft"


@pytest.mark.parametrize("start_action", ["snooze_draft"])
def test_telegram_callback_rejects_old_approve_after_snooze(audit_db: Path, allow_sender: None, start_action: str):
    first = client.post("/telegram/updates", json=_callback(start_action, 1, f"cb-{start_action}-1"))
    assert first.status_code == 200
    assert first.json()["audit_entry"]["resulting_case_state"] == "snoozed"

    stale_response = client.post("/telegram/updates", json=_callback("approve_draft", 1, "cb-approve-stale-snooze"))
    assert stale_response.status_code == 409
    assert stale_response.json()["status"] == "telegram_callback_stale_card"
    assert stale_response.json()["current_case_state"] == "snoozed"

    fresh_response = client.post("/telegram/updates", json=_callback("approve_draft", 2, "cb-approve-fresh-snooze"))
    assert fresh_response.status_code == 200
    assert fresh_response.json()["audit_entry"]["previous_case_state"] == "snoozed"
    assert fresh_response.json()["audit_entry"]["resulting_case_state"] == "approved_draft"


@pytest.mark.parametrize("start_action", ["edit_draft", "snooze_draft"])
def test_telegram_callback_approval_can_follow_deferred_states(audit_db: Path, allow_sender: None, start_action: str):
    first = client.post("/telegram/updates", json=_callback(start_action, 1, f"cb-deferred-{start_action}-1"))
    assert first.status_code == 200
    assert first.json()["audit_entry"]["resulting_case_state"] in {"edit_requested", "snoozed"}

    second = client.post("/telegram/updates", json=_callback("approve_draft", 2, f"cb-deferred-{start_action}-2"))
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
            callback_revision=1,
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
    assert isinstance(errors[0], TelegramCallbackStaleCardError)
    history = TelegramCallbackAuditStore(audit_db).get_case_history("DP-DEBT-001")
    assert len(history) == 1
    assert history[0]["resulting_case_state"] == "approved_draft"
    assert TelegramCallbackAuditStore(audit_db).get_current_case_state("DP-DEBT-001") == "approved_draft"


def test_telegram_callback_duplicate_callback_id_is_idempotent(audit_db: Path, allow_sender: None):
    callback_payload = _callback("approve_draft", 1, "cb-duplicate")

    first = client.post("/telegram/updates", json=callback_payload)
    second = client.post("/telegram/updates", json=callback_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["audit_entry"]["callback_query_id"] == "cb-duplicate"
    assert second.json()["audit_entry"]["resulting_case_state"] == "approved_draft"
    assert client.get("/cases/DP-DEBT-001/telegram/audit-history").json()["history_count"] == 1


def test_keyboard_invalidation_failure_does_not_bypass_revision_protection(
    audit_db: Path, allow_sender: None, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("backend.app.main.invalidate_telegram_callback_keyboard", lambda _payload: (_ for _ in ()).throw(TelegramLoopError("boom")))

    edit_response = client.post("/telegram/updates", json=_callback("edit_draft", 1, "cb-invalidation-edit"))
    assert edit_response.status_code == 200
    assert edit_response.json()["keyboard_invalidation"]["status"] == "failed"
    assert edit_response.json()["audit_entry"]["resulting_case_state"] == "edit_requested"

    stale_response = client.post("/telegram/updates", json=_callback("approve_draft", 1, "cb-invalidation-stale"))
    assert stale_response.status_code == 409
    assert stale_response.json()["status"] == "telegram_callback_stale_card"


@pytest.mark.parametrize(
    "case_state, expected_labels",
    [
        ("draft_pending", ["Approve", "Edit", "Snooze", "Mark done"]),
        ("edit_requested", ["Approve", "Mark done"]),
        ("snoozed", ["Approve", "Mark done"]),
        ("approved_draft", ["Mark done"]),
        ("completed", []),
    ],
)
def test_rendered_actions_match_valid_transitions_for_every_state(case_state: str, expected_labels: list[str]):
    case = {
        "case_id": "DP-DEBT-001",
        "case_type": "Debt dispute",
        "priority": "high",
        "current_stage": "investigation",
        "recommended_next_action": "Review manually",
        "extracted_deadlines": [{"date": "2026-07-21"}],
    }
    preview = build_telegram_approval_preview(case, case_state=case_state, card_revision=7)
    assert preview["approval_buttons"] == expected_labels
    assert preview["card_revision"] == 7

    payload = build_stateful_telegram_approval_payload(case, case_state=case_state, card_revision=7)
    assert payload["approval_buttons"] == expected_labels
    assert payload["card_revision"] == 7
    markup = payload["reply_markup"]["inline_keyboard"]
    rendered_labels = [button["text"] for row in markup for button in row]
    assert rendered_labels == expected_labels
    if expected_labels:
        expected_actions = approval_buttons_for_state(case_state)
        assert rendered_labels == list(expected_actions)
        assert payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("disputepilot:DP-DEBT-001:7:")
    else:
        assert markup == []


@pytest.mark.parametrize("state", ["draft_pending", "edit_requested", "snoozed", "approved_draft"])
def test_preview_action_map_matches_stateful_transition_map(state: str):
    assert list(approval_buttons_for_state(state)) == list(APPROVAL_ACTIONS_BY_STATE[state].keys())


def test_telegram_callback_persistence_survives_new_store_instance(audit_db: Path, allow_sender: None):
    response = client.post("/telegram/updates", json=_callback("mark_done", 1, "cb-restart-safe"))

    assert response.status_code == 200

    fresh_store = TelegramCallbackAuditStore(audit_db)
    history = fresh_store.get_case_history("DP-DEBT-001")
    assert len(history) == 1
    assert history[0]["callback_query_id"] == "cb-restart-safe"
    assert history[0]["resulting_case_state"] == "completed"
    assert fresh_store.get_current_case_state("DP-DEBT-001") == "completed"
