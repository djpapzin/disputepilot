from __future__ import annotations

import json
import re
from typing import Any

from backend.app.models import RedactionWarning

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]?){10,}(?!\w)")
LONG_DIGIT_RE = re.compile(r"\b\d{8,}\b")
SECRET_TOKEN_RE = re.compile(
    r"(?i)(?:\"(?:api[_-]?key|token|secret|client_secret|access_token|refresh_token|private_key|secret_key)\"\s*:|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_.-]{8,}|xox[baprs]-[A-Za-z0-9-]{10,}|api[_-]?key\s*[:=]\s*[^\s]+|token\s*[:=]\s*[^\s]+|secret\s*[:=]\s*[^\s]+)"
)


def fixture_to_text(fixture: Any) -> str:
    if isinstance(fixture, str):
        return fixture
    return json.dumps(fixture, ensure_ascii=False, sort_keys=True)


def _warning(kind: str) -> RedactionWarning:
    return RedactionWarning(type=kind, message=f"Potential {kind} pattern detected; value redacted from scanner output.")


def scan_fixture_text(fixture: Any) -> list[dict[str, str]]:
    """Scan fixture text for risky private-data patterns.

    The scanner returns pattern classes only, never matched values.
    """

    text = fixture_to_text(fixture)
    checks = [
        ("email_like", EMAIL_RE),
        ("phone_like", PHONE_RE),
        ("long_digit_like", LONG_DIGIT_RE),
        ("secret_token_like", SECRET_TOKEN_RE),
    ]
    warnings: list[dict[str, str]] = []
    for kind, pattern in checks:
        if pattern.search(text):
            warnings.append(_warning(kind).model_dump())
    return warnings


def scan_fixture(fixture: Any) -> dict[str, Any]:
    warnings = scan_fixture_text(fixture)
    return {"warning_count": len(warnings), "warnings": warnings}
