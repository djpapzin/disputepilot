from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "DisputePilot"


def _env_bool(name: str, default: bool = False) -> bool:
    """Return a truthy env value as a boolean with a conservative default."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


DEMO_MODE = _env_bool("DISPUTEPILOT_DEMO_MODE", True)

# Local integrations are intentionally off by default.
GMAIL_INTEGRATION_ENABLED = _env_bool("DISPUTEPILOT_GMAIL_INTEGRATION_ENABLED", False)
UIPATH_INTEGRATION_ENABLED = _env_bool("UIPATH_INTEGRATION_ENABLED", False)
TELEGRAM_SEND_ENABLED = _env_bool("DISPUTEPILOT_TELEGRAM_SEND_ENABLED", False)

# UiPath Maestro Case handoff settings.
UIPATH_TENANT_URL = os.getenv("UIPATH_TENANT_URL", "").rstrip("/")
UIPATH_CLIENT_ID = os.getenv("UIPATH_CLIENT_ID", "")
UIPATH_CLIENT_SECRET = os.getenv("UIPATH_CLIENT_SECRET", "")
UIPATH_QUEUE_NAME = os.getenv("UIPATH_QUEUE_NAME", "DisputePilot Cases")
UIPATH_WEBHOOK_URL = os.getenv("UIPATH_WEBHOOK_URL", "").rstrip("/")
UIPATH_AUTH_TOKEN = os.getenv("UIPATH_AUTH_TOKEN", "")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = PROJECT_ROOT / "demo-data" / "cases"


def get_integrations() -> dict[str, bool]:
    return {
        "gmail": GMAIL_INTEGRATION_ENABLED,
        "uipath": UIPATH_INTEGRATION_ENABLED,
        "telegram_send": TELEGRAM_SEND_ENABLED,
    }


INTEGRATIONS = get_integrations()
