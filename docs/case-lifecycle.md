# Common Case Lifecycle

DisputePilot models recurring dispute patterns as a shared lifecycle. A case may skip some stages or loop through stages more than once, but the model gives UiPath Maestro Case a stable workflow structure.

```text
problem_event
  -> initial_complaint
  -> company_acknowledgement
  -> company_response
  -> regulator_or_ombud_escalation
  -> participant_response
  -> response_gap_detection
  -> rebuttal_or_followup
  -> deadline_tracking
  -> settlement_or_closure
```

## Stage definitions

| Stage | Meaning | DisputePilot intelligence task | Redaction warning |
| --- | --- | --- | --- |
| `problem_event` | The incident that created the dispute, such as a disputed balance, failed refund, rejected insurance claim, missing delivery, or credit bureau listing. | Capture a synthetic incident summary, impacted product/service, amount band, and first known date. | Real statements, transaction IDs, policy IDs, order numbers, screenshots, and account identifiers must be replaced with synthetic placeholders. |
| `initial_complaint` | The first complaint or dispute message sent to a company or collector. | Identify requested remedy, disputed facts, supporting evidence, and target department. | Do not copy exact private complaint wording; summarize in generalized form. |
| `company_acknowledgement` | The company confirms receipt, gives a reference, or promises investigation. | Extract acknowledgement date, response SLA, reference type, and any next-step request. | Replace case/reference numbers and contact details with fictional examples. |
| `company_response` | The company responds with approval, rejection, partial answer, proof request, or generic template. | Detect whether the response answers the complaint, requests proof, gives a deadline, or creates a new dispute gap. | Do not include real attachments, staff names, or quoted private response text. |
| `regulator_or_ombud_escalation` | The case is escalated to a regulator, ombud, compliance body, bureau, or dispute platform. | Identify likely escalation body and convert the complaint into a structured packet. | Use fictional escalation references only. |
| `participant_response` | The company, collector, bureau, insurer, or operator responds inside an escalation process. | Compare response content against the original complaint and evidence matrix. | Redact legal names, account numbers, IDs, claim numbers, and official references. |
| `response_gap_detection` | DisputePilot detects unanswered points, missing evidence, conflicting balances, or unresolved deadlines. | Generate a gap list and severity rating. | Keep gaps generalized; do not quote exact private evidence. |
| `rebuttal_or_followup` | The user needs to reply, dispute the response, request proof, or chase non-compliance. | Draft a concise rebuttal/follow-up outline for human approval. | Use synthetic facts and placeholders. |
| `deadline_tracking` | A deadline exists for proof, rebuttal, payment hold, claim appeal, refund reflection, or ombud response. | Extract dates and create tasks/reminders. | Do not expose private calendar invites or email metadata. |
| `settlement_or_closure` | The dispute is resolved, corrected, refunded, closed, or moved to long-term monitoring. | Log outcome, remaining risks, and confirmation proof required. | Replace settlement letters, corrected statements, and final emails with synthetic summaries. |

## Lifecycle loops

Disputes often loop between `company_response`, `response_gap_detection`, and `rebuttal_or_followup`. DisputePilot should treat each loop as a timeline event, not overwrite earlier history.

## UiPath Maestro Case handoff

Each stage should map to a Maestro Case state, queue item, or task with:

- case ID;
- current lifecycle stage;
- priority;
- extracted deadline;
- missing evidence list;
- next recommended action;
- human approval state;
- redaction requirement flag.
