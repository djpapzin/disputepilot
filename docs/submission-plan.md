# DisputePilot Submission Plan

## Hackathon context

- Event: UiPath AgentHack
- Product name: DisputePilot
- Target track: UiPath Maestro Case
- Repository: `djpapzin/disputepilot`

## Product positioning

DisputePilot is an AI case manager for deadline-sensitive emails and disputes. UiPath Automation Cloud / Maestro Case coordinates the case lifecycle, while AI services classify messages, extract deadlines and risks, draft replies, and route approval to a human through Telegram.

Hermes and Codex are build tools only and must not be presented as the submitted product.

## MVP scope

### Inputs

- Synthetic email/demo messages from `demo-data/`.
- No real Gmail or dispute data.

### Case flow

1. Ingest a demo message.
2. Classify the message.
3. Create a UiPath Maestro Case record/task.
4. Extract deadline, risk, and suggested action.
5. Draft a response.
6. Send approval prompt to Telegram.
7. Handle one of: Approve, Edit, Snooze, Mark done.
8. Log the outcome.

### Demo cases

| Case | Purpose |
| --- | --- |
| Debt dispute deadline | Show urgency detection and deadline routing. |
| Service delivery/billing escalation | Show complaint classification and escalation summary. |
| Job/opportunity reply needed | Show non-dispute but time-sensitive follow-up handling. |

## Human approval options

- Approve
- Edit
- Snooze
- Mark done

## Submission guardrails

- Keep repo public before submission.
- Keep all examples synthetic.
- Do not include real personal emails, real dispute names, named real company dispute data, account numbers, IDs, or private email addresses.
- Do not commit `.env` or secrets.
