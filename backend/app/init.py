from __future__ import annotations

from backend.app.fixture_loader import load_cases
from backend.app.pipeline import analyze_case


def initialize_demo_state() -> dict[str, object]:
    cases = load_cases()
    return {
        "demo_mode": True,
        "case_count": len(cases),
        "case_ids": [case["case_id"] for case in cases],
    }


def analyze_all_demo_cases() -> list[dict[str, object]]:
    return [analyze_case(case) for case in load_cases()]
