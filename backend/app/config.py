from pathlib import Path

APP_NAME = "DisputePilot"
DEMO_MODE = True
GMAIL_INTEGRATION_ENABLED = False
UIPATH_INTEGRATION_ENABLED = False
TELEGRAM_SEND_ENABLED = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = PROJECT_ROOT / "demo-data" / "cases"

INTEGRATIONS = {
    "gmail": GMAIL_INTEGRATION_ENABLED,
    "uipath": UIPATH_INTEGRATION_ENABLED,
    "telegram_send": TELEGRAM_SEND_ENABLED,
}
