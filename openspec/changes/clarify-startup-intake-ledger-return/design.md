## Context

FlowPilot startup now runs under a daemon-owned two-table control plane. The
native startup intake UI still returns a result path, but the foreground
Controller must resume from Router daemon status and the Controller action
ledger after the UI closes. Existing wording in the skill and Router action
metadata still uses direct-apply language from the pre-daemon flow.

## Goals / Non-Goals

**Goals:**

- Make the startup-intake handoff prompt short and ledger-oriented.
- Avoid adding a new decision tree to the prompt.
- Preserve sealed startup intake body handling and existing Router receipt
  mechanics.
- Add focused regression coverage for stale direct-apply wording.

**Non-Goals:**

- No new startup table, action type, payload schema, or Router reconciliation
  mechanism.
- No change to PM access to the sealed user intake.
- No broad rewrite of Controller, startup, or heartbeat prompt text.

## Decisions

- Use "return to Router daemon status and the Controller action ledger" as the
  main wording. This keeps authority with the existing work board instead of
  teaching Controller custom if/then rules.
- Keep direct `startup_intake_result.result_path` language in the payload
  contract. The contract remains useful, but the surrounding instruction must
  not imply that direct `apply` is always the next action.
- Add prompt-boundary checks alongside focused runtime tests rather than
  relying only on human review of prompt text.

## Risks / Trade-offs

- Prompt wording may become too vague for direct non-daemon tests. Mitigation:
  keep the payload contract explicit and verify direct startup action tests
  still pass.
- String checks can become brittle. Mitigation: assert only the important
  negative wording and the ledger-oriented replacement phrase.
