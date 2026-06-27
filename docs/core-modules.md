# Core Modules

DisputePilot is organized as modular dispute intelligence capabilities that can be orchestrated by UiPath Maestro Case.

## Module overview

| Module | Purpose | Inputs | Outputs | Demo/privacy guardrail |
| --- | --- | --- | --- | --- |
| Label-to-case importer | Converts generalized Gmail-label-derived patterns into structured cases. | Synthetic label names, synthetic thread summaries, demo fixtures. | Case type, priority, source label, initial stage. | Never import real Gmail bodies or attachments into the repo. |
| Thread timeline builder | Turns message summaries into ordered case events. | Synthetic event summaries, dates, actors, stage tags. | `timeline_events` list and lifecycle state. | Use synthetic actors and generalized event text only. |
| Evidence matrix | Tracks evidence needed, evidence available, and proof gaps. | Synthetic proof items such as invoice placeholder, screenshot placeholder, statement placeholder. | Evidence rows with status and redaction notes. | Mark where real evidence would require redaction; do not store real proof. |
| Deadline extractor | Finds response deadlines, appeal windows, refund reflection dates, and compliance due dates. | Synthetic summaries and fictional dates. | `extracted_deadlines` with date, type, source, and confidence. | Never copy private email metadata or calendar data. |
| Response-gap detector | Identifies unanswered points, template replies, missing proof, inconsistent amounts, or unsupported repudiations. | Company response summary and original complaint summary. | Gap list, severity, and recommended follow-up. | Summarize gaps; do not quote exact private correspondence. |
| Balance/amount reconciliation helper | Compares claimed, paid, refunded, credited, and disputed amounts. | Synthetic amount entries and timeline events. | Disputed amount table and discrepancy flags. | Use fictional amounts and demo references only. |
| Escalation/rebuttal drafter | Creates concise next-response outlines for human approval. | Case summary, gaps, missing evidence, regulator fit, deadline. | Draft outline, requested remedy, proof checklist. | Drafts must remain fictional in fixtures. |
| Telegram approval cards | Converts recommended actions into reviewable cards. | Case ID, priority, deadline, recommended action, draft outline. | Approve/Edit/Snooze/Mark done preview. | Do not include sensitive proof or private identifiers in card previews. |
| Redaction/synthetic demo mode | Enforces demo-safe output and redaction warnings. | Case data, fixture metadata, configured demo mode. | `redaction_required` flag and warnings. | Default mode for hackathon fixtures; no real data allowed. |
| UiPath Maestro Case handoff | Packages case intelligence for workflow orchestration. | Structured case object, lifecycle stage, deadlines, tasks. | UiPath case payload fields and stage mapping. | Handoff payloads in repo must use placeholders only. |

## Module details

### Label-to-case importer

Maps generalized source categories such as `telecom_debt_collector_dispute` or `cellphone_insurance_repudiation` into a case type and starting lifecycle stage.

### Thread timeline builder

Builds a clean chronological record from synthetic summaries:

1. problem event;
2. initial complaint;
3. acknowledgement;
4. company or participant response;
5. escalation;
6. rebuttal/follow-up;
7. settlement or closure.

### Evidence matrix

Tracks each proof item with:

- item name;
- status: available, missing, requested, redaction_required, or not_applicable;
- why it matters;
- safe synthetic description.

### Deadline extractor

Extracts and normalizes deadlines into:

- date;
- deadline type;
- source event;
- action required;
- confidence.

### Response-gap detector

Flags common gaps:

- company did not address the main complaint;
- no proof supplied;
- deadline missing or ambiguous;
- balance/refund does not reconcile;
- repudiation reason unsupported;
- template response ignores evidence.

### Balance/amount reconciliation helper

Compares fictional amount fields and generates follow-up prompts when:

- an approved refund has not reflected;
- billed amount differs from quoted amount;
- collector balance differs from account history;
- partial credit does not close the dispute.

### Escalation/rebuttal drafter

Generates draft outlines, not final sent messages, until approved. Each outline should include:

- opening reference;
- facts in dispute;
- evidence checklist;
- response gaps;
- requested remedy;
- deadline or escalation warning.

### Telegram approval cards

Every approval card should present minimal, non-sensitive information:

- case ID;
- case type;
- priority;
- deadline;
- recommended next action;
- approval buttons: Approve, Edit, Snooze, Mark done.

### Redaction/synthetic demo mode

This mode is mandatory for repository fixtures. It should block or warn on private data classes such as names, private email addresses, phone numbers, account numbers, ID numbers, case numbers, attachments, screenshots, and exact private message content.

### UiPath Maestro Case handoff

The handoff module prepares fields for Maestro Case orchestration:

- case ID;
- current stage;
- priority;
- due date;
- assigned queue/action;
- missing evidence;
- recommended response;
- Telegram approval state;
- redaction status.
