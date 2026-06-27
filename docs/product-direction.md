# Product Direction: DisputePilot

## Positioning

DisputePilot is a **case intelligence layer for disputes**, not just an email scanner. It converts messy, deadline-sensitive correspondence into a structured case view that helps a person decide what to do next.

The product is designed for UiPath AgentHack with **UiPath Automation Cloud / Maestro Case** as the workflow orchestration layer. DisputePilot supplies the dispute intelligence: classification, timeline building, evidence gaps, deadline and risk extraction, response-gap detection, and draft next actions.

> **Core promise:** “Detect what needs action, build the case timeline, identify missing proof, draft the next response, and route approval through Telegram while UiPath Maestro Case orchestrates the workflow.”

## What DisputePilot does

DisputePilot looks across labelled dispute-style messages and turns generalized patterns into case tasks:

1. **Detect what needs action** — identify messages that contain deadlines, unresolved complaints, financial exposure, repudiations, refunds, or proof requests.
2. **Build the case timeline** — organize events such as the problem event, complaint, acknowledgement, response, escalation, rebuttal, and closure.
3. **Identify missing proof** — map what evidence exists, what evidence is missing, and which items should be redacted before demo or sharing.
4. **Draft the next response** — create concise response outlines for human review, including missing-proof requests and rebuttal points.
5. **Route human approval** — turn each recommendation into a Telegram approval card with Approve, Edit, Snooze, and Mark done options.
6. **Hand off orchestration** — send structured case fields and status to UiPath Maestro Case for workflow tracking.

## What DisputePilot is not

- It is not a raw Gmail archive copier.
- It is not a replacement for legal, regulatory, or financial advice.
- It is not an autonomous sender of private replies without human approval.
- It does not require real private emails or attachments for the demo.
- Hermes and Codex are build tools only; they are not part of the submitted product experience.

## Privacy-first demo direction

The hackathon demo must use synthetic examples only. Real dispute emails, attachments, screenshots, statements, case numbers, account numbers, phone numbers, ID numbers, private names, and exact wording must not be copied into the repository.

Where sensitive evidence would normally exist, demo records should use a redaction warning such as:

> Redaction required: replace private statements, screenshots, account numbers, IDs, phone numbers, case references, and exact email content with synthetic summaries before demo use.

## Strategic product framing

DisputePilot should feel like a command center for recurring consumer and account disputes:

- **Case-first:** every message is interpreted as part of a case lifecycle, not an isolated email.
- **Evidence-aware:** the system tracks proof needed for escalation, not just text summaries.
- **Deadline-sensitive:** deadlines and response gaps become visible tasks.
- **Human-approved:** replies and actions are suggested, then routed for approval.
- **UiPath-orchestrated:** Maestro Case coordinates the durable workflow and case state.
