# DisputePilot Architecture

## Goal

DisputePilot is an AI case manager for deadline-sensitive emails and disputes. It turns unstructured email/demo messages into trackable cases with deadline, risk, draft-response, and human-approval steps.

## Target track

- **UiPath AgentHack target track:** UiPath Maestro Case
- **Primary orchestrator:** UiPath Automation Cloud / Maestro Case
- **Human approval channel:** Telegram topic/thread for the hackathon demo

## End-to-end flow

```text
email/demo message
  -> classify
  -> create UiPath case
  -> extract deadline/risk
  -> draft reply
  -> Telegram approval
  -> log outcome
```

## Components

| Component | Responsibility |
| --- | --- |
| Demo message source | Supplies synthetic email-like examples for the hackathon demo. |
| Classifier | Labels the message as debt dispute, service/billing escalation, job/opportunity, or other. |
| UiPath Maestro Case | Creates and orchestrates the case state, tasks, deadlines, and escalation steps. |
| Extraction service | Pulls out dates, risk level, required action, and evidence fields. |
| Drafting service | Produces a short suggested reply or action summary. |
| Telegram approval | Lets a human choose state-aware actions with revision-guarded callbacks. |
| Outcome logger | Records the decision, timestamp, and next action. |

## MVP demo cases

1. **Debt dispute deadline** — a synthetic collections-style deadline requires a timely reply.
2. **Service delivery/billing escalation** — a synthetic billing/service issue needs escalation and evidence capture.
3. **Job/opportunity reply needed** — a synthetic opportunity email needs prioritisation and a timely response.

## Privacy and data boundaries

- Use synthetic fixtures only.
- Do not include real Gmail messages, private dispute data, real account numbers, IDs, or private email addresses.
- Do not commit secrets or project-local `.env` files.
- Hermes/Codex may be used as build tools, but they are not part of the submitted product branding.
