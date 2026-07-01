# DisputePilot Submission Runbook

## Repo and track
- **Repository:** https://github.com/djpapzin/disputepilot
- **Hackathon:** UiPath AgentHack
- **Track:** UiPath Maestro Case
- **Status:** Demo-ready (synthetic mode)

## 1) What is implemented
DisputePilot currently includes the **Phase 3 synthetic workflow skeleton**:
- Synthetic fixture loader for demo cases (`demo-data/cases/`)
- API endpoints:
  - `GET /health`
  - `GET /cases`
  - `GET /cases/{case_id}`
  - `POST /cases/{case_id}/analyze`
  - `GET /demo`
- Case analysis enrichments:
  - deadline extraction
  - risk signals and missing evidence matrix
  - response gap / reconciliation heuristics
  - redaction warning enforcement in demo payloads
- **New in this cycle**:
  - `workflow_handoff_preview` field in `/analyze`
  - `telegram_approval_preview` field in `/analyze`

> Actual external integrations (UiPath API, Telegram bot send, live Gmail polling) are intentionally stubbed as previews in this synthetic phase.

## 2) How to run locally (quick)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 3) Smoke test commands
```bash
# API health
curl http://127.0.0.1:8000/health

# List synthetic cases
curl http://127.0.0.1:8000/cases

# Analyze one sample case
curl -X POST http://127.0.0.1:8000/cases/DP-DEBT-001/analyze

# Demo summary
curl http://127.0.0.1:8000/demo
```

Expected checks:
- `/health` returns `{"status":"ok","demo_mode":true,...}`
- `/cases` returns synthetic fixture list and count
- `/analyze` returns a JSON object containing:
  - `workflow_handoff_preview`
  - `telegram_approval_preview`
  - `redaction_scan`
- Unknown case IDs return clear 404-like detail (`Synthetic case not found`).

## 4) Test command
```bash
pytest -q
```

Current baseline in repo: **25 passed**.

## 5) Submission checklist (submit now)
- [ ] Public repo URL shared
- [ ] `README.md` includes project summary + run instructions
- [ ] Demo endpoint works and includes new preview payloads
- [ ] No real sensitive data committed (synthetic fixtures only)
- [ ] No secrets or `.env` secrets committed
- [ ] Short walkthrough prepared for judges:
  - call `/demo`
  - call `/cases`
  - call `/cases/DP-DEBT-001/analyze`
  - show `Approve / Edit / Snooze / Mark done` preview intent

## 6) Limitations (explicitly state)
- No live external integrations in this phase.
- Telegram payloads are preview cards, not actually sent.
- UiPath handoff payload is integration preview, not an active orchestration call.
