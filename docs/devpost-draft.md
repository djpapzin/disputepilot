# DisputePilot – UiPath AgentHack Devpost Draft Copy

## Project title
DisputePilot

## Team / Repo
- GitHub: https://github.com/djpapzin/disputepilot

## Track
UiPath AgentHack: **UiPath Maestro Case**

## Problem
Disputes and complaint emails arrive with deadlines, missing proof, and unclear next actions, causing slow, inconsistent handling.

## Solution
DisputePilot turns a synthetic demo message into an actionable case package:
- detects case type and priority,
- extracts deadlines and risk signals,
- identifies evidence gaps,
- drafts a response outline for human approval,
- and exposes **UiPath + Telegram workflow previews** for orchestration and review.

## Technical approach
- Synthetic-first FastAPI demo skeleton (`/cases`, `/cases/{case_id}`, `/cases/{case_id}/analyze`, `/demo`).
- Structured case intelligence pipeline.
- Privacy-by-design redaction guardrails.
- UiPath Orchestra and Telegram approval flows represented as previews until live integrations are enabled.

## Judge demo script (3 minutes)
1. Open README and run setup.
2. Start API and call `/health`.
3. Show `/cases` and pick `DP-DEBT-001`.
4. POST `/cases/DP-DEBT-001/analyze` and highlight:
   - `workflow_handoff_preview`
   - `telegram_approval_preview`
   - redaction + deadline metadata
5. Show `/demo` summary and how multiple cases are ranked.

## Built-in constraints (important)
This phase uses synthetic-only data and preview integrations only. No real emails, accounts, or private case records are included in the repository.

## Future work after hackathon
- Wire real UiPath Maestro Case API calls.
- Replace preview Telegram cards with bot-sent inline approval messages.
- Add durable orchestration trace and logging persistence.
