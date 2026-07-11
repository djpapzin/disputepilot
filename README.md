# DisputePilot

DisputePilot is an AI case manager for deadline-sensitive emails and disputes, created for the UiPath AgentHack hackathon.

## Product summary

DisputePilot watches incoming emails or demo messages, classifies the case type, extracts deadlines and risk signals, drafts a reply, and routes the decision to a human approver before anything is sent or marked complete.

## Orchestration layer

UiPath Automation Cloud / Maestro Case is the orchestration layer for the product. The intended demo flow is:

```text
email/demo message -> classify -> create UiPath case -> extract deadline/risk -> draft reply -> Telegram approval -> log outcome
```

AI services support the flow by:

- classifying emails and dispute messages;
- extracting deadlines, risks, account/action references, and next steps;
- drafting concise replies for human review;
- routing approval actions through Telegram;
- logging outcomes for case follow-up.

## Human approval actions

The MVP approval options are:

- **Approve** — accept the drafted reply/action.
- **Edit** — request changes before approval.
- **Snooze** — defer the case until a later reminder.
- **Mark done** — close/log the case without sending a reply.

## MVP demo cases

The repository contains only synthetic demo cases (demo fixtures only):

1. Telecom debt collector dispute with deadline pressure.
2. Service delivery or billing escalation.
3. Job or opportunity reply needed.
4. Retail credit bureau correction.
5. Gambling operator deposit/ledger refund disputes.
6. Device insurance repudiation.

## Submission support

- Runbook: [docs/submission-ready-runbook.md](docs/submission-ready-runbook.md)
- Devpost draft copy: [docs/devpost-draft.md](docs/devpost-draft.md)

## Build-tool disclosure

Hermes and Codex are AI coding/build tools used to create this repository and the demo implementation. They are not the submitted product. The submitted product is **DisputePilot**.

## Privacy guardrails

No real personal emails, real dispute data, account numbers, IDs, private email addresses, or private attachments are included in this repository. Demo fixtures are synthetic and must stay synthetic.

## Synthetic demo data only

This repository contains fictionalized fixtures and generalized dispute-intelligence patterns only. Real dispute emails, Gmail threads, statements, screenshots, attachments, account numbers, phone numbers, ID numbers, case references, private names, and exact private wording are not included.

Where a real case would require supporting evidence, the docs and JSON fixtures use synthetic summaries plus redaction warnings. Any future demo or integration must keep private evidence outside the public repo unless it has been explicitly redacted and approved for use.

## Phase 3 API skeleton

Phase 3 adds a minimal runnable FastAPI app skeleton for synthetic demos only. It loads the fictional JSON fixtures in `demo-data/cases/`, runs a placeholder case intelligence pipeline, and returns Telegram/UiPath preview payloads without calling any external service.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

If editable installs are not needed, install the runtime dependencies directly:

```bash
python -m pip install fastapi 'uvicorn[standard]' pytest httpx
```

### Run the API

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Run tests

```bash
pytest -q
```

### Example curl commands

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/cases
curl http://127.0.0.1:8000/cases/DP-DEBT-001
curl -X POST http://127.0.0.1:8000/cases/DP-DEBT-001/analyze
curl -X POST http://127.0.0.1:8000/cases/DP-DEBT-001/handoff
curl -X POST http://127.0.0.1:8000/cases/DP-DEBT-001/telegram/notify
curl -X POST http://127.0.0.1:8000/telegram/updates -H 'Content-Type: application/json' -d '{"callback_query":{"id":"cb-1","from":{"id":123456},"data":"disputepilot:DP-DEBT-001:approve_draft"}}'
curl http://127.0.0.1:8000/cases/DP-DEBT-001/telegram/audit-history
```

### Demo explanation

- `/health` confirms demo mode and shows the current integration flags.
- `/cases` lists synthetic fixtures only.
- `/cases/{case_id}` returns the raw synthetic fixture.
- `/cases/{case_id}/analyze` returns normalized case intelligence plus Telegram, UiPath, workflow handoff, and Telegram approval preview payloads.
- `/cases/{case_id}/handoff` sends an optional live UiPath handoff when `uipath` integration flags are enabled; otherwise it returns a handoff preview payload.
- `/cases/{case_id}/telegram/notify` sends an optional live Telegram approval card when send is enabled; otherwise it returns a preview payload.
- `/telegram/updates` parses, validates, and persists Telegram callback actions for the synthetic case approval workflow.
- `/cases/{case_id}/telegram/audit-history` returns a redacted public audit trail for a case.
- `/demo` returns a compact summary across all synthetic cases.

The `/cases/{case_id}/handoff` route is integration-ready and uses optional `UIPATH_WEBHOOK_URL`/`UIPATH_INTEGRATION_ENABLED` settings; when disabled it is intentionally safe and preview-only.

## Agent status reporting

Hermes task updates for this repository must use GitHub as the canonical record. See [docs/agent-status-contract.md](docs/agent-status-contract.md) for the required branch, PR, final comment, privacy, and Telegram-topic rules.

## Repository status

This repo currently contains product/spec docs, synthetic fixtures, and the Phase 3 FastAPI skeleton. The full integration app will be designed later.
