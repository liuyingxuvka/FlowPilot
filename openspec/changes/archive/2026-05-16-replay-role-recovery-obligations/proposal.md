## Why

FlowPilot currently treats role recovery as a PM-facing freshness checkpoint even when the recovery is purely mechanical. That adds an avoidable PM round trip and leaves the recovered role's outstanding ACK or work obligations unresolved until a later decision.

This change makes role recovery operational: once a role is restored or replaced from current-run memory, Router settles or reissues that role's outstanding obligations directly, while preserving PM authority only for semantic conflicts, ambiguous ownership, or route-changing decisions.

## What Changes

- Add a Router-owned recovery step that scans all current wait rows, card return waits, and packet ownership records for the recovered role.
- Settle already-valid ACKs or output envelopes without asking the recovered role to redo them.
- Generate replacement ACK or work obligations only for missing, invalid, stale, or superseded evidence.
- Preserve original task order when multiple obligations must be reissued.
- Mark original wait rows as `superseded` only after their replacement row has been durably created and linked.
- Keep Controller as a relay/status actor: it may submit Router-authored replacement rows but may not invent work or infer completion from chat history.
- Notify PM only when mechanical recovery cannot safely decide continuation, such as conflicting outputs, unclear packet ownership, repeated recovery failure, or route/acceptance changes.

## Capabilities

### New Capabilities

- `role-recovery-obligation-replay`: Defines Router behavior for settling or reissuing outstanding obligations after a background role is mechanically restored or replaced.

### Modified Capabilities

- None.

## Impact

- Affected runtime code: `skills/flowpilot/assets/flowpilot_router.py` and supporting runtime ledger helpers if needed.
- Affected models/checks: role recovery, wait reconciliation, controller action ledger, two-table async scheduler, and resume/continuation FlowGuard coverage.
- Affected tests: router runtime tests that cover recovery, ACK waits, output waits, replacement rows, and superseded rows.
- PM workflow impact: PM receives recovery escalation only for semantic or ambiguous states, not for successful mechanical replay of the recovered role's existing obligations.
