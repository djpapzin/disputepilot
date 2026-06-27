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

The repository contains only synthetic demo cases:

1. Debt dispute deadline.
2. Service delivery or billing escalation.
3. Job or opportunity reply needed.

## Build-tool disclosure

Hermes and Codex are AI coding/build tools used to create this repository and the demo implementation. They are not the submitted product. The submitted product is **DisputePilot**.

## Privacy guardrails

No real personal emails, real dispute data, account numbers, IDs, private email addresses, or private attachments are included in this repository. Demo fixtures are synthetic and must stay synthetic.

## Repository status

This bootstrap stops at repository setup and product/spec documentation. The full app will be designed next.
