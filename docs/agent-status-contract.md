# DisputePilot Agent Status Reporting Contract

DisputePilot uses GitHub as the source of truth for Hermes task completion, blockers, review status, and next actions. Telegram can still receive short human-friendly progress updates in topic `26278`, but Telegram-only updates must never be the final task record.

Hermes is the AI coding/build agent for this repository. Hermes, Codex, OpenClaw, and other build tools are not part of the DisputePilot product.

## Scope

This contract applies to every Hermes task for `djpapzin/disputepilot`, including docs, code, tests, integrations, reviews, monitoring, and follow-up fixes.

## Required workflow

Every Hermes task must:

1. Work on a named branch.
2. Open or update a GitHub PR for the task when code, docs, config, tests, or product artifacts are changed.
3. Post a final PR comment using the structured `DISPUTEPILOT_AGENT_STATUS` block below.
4. Include blockers and a clear next recommended action.
5. Never include secrets or real private dispute data.
6. Never rely on Telegram-only updates as the final record.

If a task does not create a PR, Hermes must open or update a GitHub issue and post the same status block as an issue comment.

## Required final PR or issue comment

```text
DISPUTEPILOT_AGENT_STATUS
status: done | blocked | needs_review | needs_user_decision
repo: djpapzin/disputepilot
branch:
pr_url:
commit:
tests:
privacy_check:
secret_check:
integrations_touched:
files_changed:
summary:
blockers:
next_recommended_action:
next_goal_suggestion:
safe_to_merge: yes | no | unknown
```

## Field rules

- `status`: Use `done`, `blocked`, `needs_review`, or `needs_user_decision`.
- `repo`: Always use `djpapzin/disputepilot`.
- `branch`: Name the working branch.
- `pr_url`: Link the PR when one exists. If no PR exists, explain why and use a GitHub issue instead.
- `commit`: Include the latest commit hash for the task.
- `tests`: State what was run. If tests were not run, say why.
- `privacy_check`: Confirm no real Gmail data, dispute evidence, account numbers, emails, IDs, private attachments, or exact private wording were posted.
- `secret_check`: Confirm no secrets, API keys, tokens, private env values, credentials, or screenshots of secrets were posted.
- `integrations_touched`: List external systems touched, or `none`.
- `files_changed`: List changed files.
- `summary`: Give a concise durable summary of what changed or what was found.
- `blockers`: If blocked, state exactly what input or approval is needed from the owner. If not blocked, use `none`.
- `next_recommended_action`: Always include a clear owner or agent next step.
- `next_goal_suggestion`: Include the next useful agent goal when another step is useful; otherwise use `none`.
- `safe_to_merge`: Use `yes`, `no`, or `unknown`, with a short reason.

## Privacy and safety rules

Do not post any of the following in PRs, issues, comments, logs, screenshots, or attachments:

- real Gmail data;
- private dispute evidence;
- account numbers;
- personal email addresses;
- phone numbers or ID numbers;
- API keys, tokens, secrets, passwords, OAuth material, or private env values;
- real statements, screenshots, attachments, or exact private wording.

Use synthetic demo data or redacted/generalized summaries only.

## Telegram rule

Send short progress updates to the DisputePilot Telegram topic when useful:

```text
Use thread/topic: 26278.
```

The final durable record must still be a GitHub PR or issue comment using `DISPUTEPILOT_AGENT_STATUS`.
