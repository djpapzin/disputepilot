from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_INITIAL_CASE_STATE = "draft_pending"

SUPPORTED_ACTION_TO_STATE = {
    "draft_pending": {
        "approve_draft": "approved_draft",
        "edit_draft": "edit_requested",
        "snooze_draft": "snoozed",
        "mark_done": "completed",
    },
    "edit_requested": {
        "approve_draft": "approved_draft",
        "mark_done": "completed",
    },
    "snoozed": {
        "approve_draft": "approved_draft",
        "mark_done": "completed",
    },
    "approved_draft": {},
    "completed": {},
}


class TelegramCallbackAuditError(RuntimeError):
    """Raised when Telegram callback persistence fails."""


class TelegramCallbackTransitionError(TelegramCallbackAuditError):
    """Raised when a callback attempts an invalid state transition."""


class TelegramCallbackAuditStore:
    """Lightweight SQLite-backed audit log for Telegram callback approvals."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_callback_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    callback_query_id TEXT NOT NULL UNIQUE,
                    authorized_sender_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    previous_case_state TEXT NOT NULL,
                    resulting_case_state TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_telegram_callback_audit_case_id ON telegram_callback_audit(case_id, id)"
            )
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _idempotency_key(callback_query_id: str) -> str:
        return hashlib.sha256(callback_query_id.encode("utf-8")).hexdigest()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "case_id": row["case_id"],
            "action": row["action"],
            "callback_query_id": row["callback_query_id"],
            "authorized_sender_id": row["authorized_sender_id"],
            "timestamp": row["timestamp"],
            "previous_case_state": row["previous_case_state"],
            "resulting_case_state": row["resulting_case_state"],
            "idempotency_key": row["idempotency_key"],
        }

    @staticmethod
    def _public_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "action": row["action"],
            "previous_case_state": row["previous_case_state"],
            "resulting_case_state": row["resulting_case_state"],
        }

    def get_case_history(self, case_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT case_id, action, callback_query_id, authorized_sender_id, timestamp,
                       previous_case_state, resulting_case_state, idempotency_key
                FROM telegram_callback_audit
                WHERE case_id = ?
                ORDER BY id ASC
                """,
                (case_id,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_public_case_history(self, case_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT action, previous_case_state, resulting_case_state
                FROM telegram_callback_audit
                WHERE case_id = ?
                ORDER BY id ASC
                """,
                (case_id,),
            ).fetchall()
        return [self._public_row(row) for row in rows]

    def get_current_case_state(self, case_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT resulting_case_state
                FROM telegram_callback_audit
                WHERE case_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return str(row["resulting_case_state"])

    def get_by_callback_query_id(self, callback_query_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT case_id, action, callback_query_id, authorized_sender_id, timestamp,
                       previous_case_state, resulting_case_state, idempotency_key
                FROM telegram_callback_audit
                WHERE callback_query_id = ?
                LIMIT 1
                """,
                (callback_query_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def record_callback(
        self,
        *,
        case_id: str,
        action: str,
        callback_query_id: str,
        authorized_sender_id: int,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        idempotency_key = self._idempotency_key(callback_query_id)
        timestamp = timestamp or self._now()

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT case_id, action, callback_query_id, authorized_sender_id, timestamp,
                       previous_case_state, resulting_case_state, idempotency_key
                FROM telegram_callback_audit
                WHERE callback_query_id = ?
                LIMIT 1
                """,
                (callback_query_id,),
            ).fetchone()
            if existing is not None:
                return {**self._row_to_dict(existing), "duplicate": True}

            current_case_state_row = conn.execute(
                """
                SELECT resulting_case_state
                FROM telegram_callback_audit
                WHERE case_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
            current_case_state = (
                str(current_case_state_row["resulting_case_state"]) if current_case_state_row is not None else DEFAULT_INITIAL_CASE_STATE
            )

            valid_transitions = SUPPORTED_ACTION_TO_STATE.get(current_case_state, {})
            if action not in valid_transitions:
                raise TelegramCallbackTransitionError(
                    f"Unsupported transition from '{current_case_state}' using action '{action}'."
                )

            resulting_case_state = valid_transitions[action]

            try:
                conn.execute(
                    """
                    INSERT INTO telegram_callback_audit (
                        case_id, action, callback_query_id, authorized_sender_id,
                        timestamp, previous_case_state, resulting_case_state, idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        action,
                        callback_query_id,
                        authorized_sender_id,
                        timestamp,
                        current_case_state,
                        resulting_case_state,
                        idempotency_key,
                    ),
                )
            except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive race fallback
                conn.rollback()
                existing = conn.execute(
                    """
                    SELECT case_id, action, callback_query_id, authorized_sender_id, timestamp,
                           previous_case_state, resulting_case_state, idempotency_key
                    FROM telegram_callback_audit
                    WHERE callback_query_id = ?
                    LIMIT 1
                    """,
                    (callback_query_id,),
                ).fetchone()
                if existing is not None:
                    return {**self._row_to_dict(existing), "duplicate": True}
                raise TelegramCallbackAuditError("Failed to persist Telegram callback audit record.") from exc
            conn.commit()

        return {
            "case_id": case_id,
            "action": action,
            "callback_query_id": callback_query_id,
            "authorized_sender_id": authorized_sender_id,
            "timestamp": timestamp,
            "previous_case_state": current_case_state,
            "resulting_case_state": resulting_case_state,
            "idempotency_key": idempotency_key,
            "duplicate": False,
        }
