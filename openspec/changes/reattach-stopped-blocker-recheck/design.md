## Context

The existing runtime already has the right clearing mechanism:
`_clear_semantic_blockers_for_pass()` clears active/awaiting recheck blockers
after the owning gate returns a passing outcome. The missing edge is from a
PM-stopped blocker back into that recheck path.

## Goals / Non-Goals

**Goals:**

- Add one explicit current-runtime recovery resolution:
  `reattach_required_recheck`.
- Require explicit user intent before leaving `wait_for_resume`.
- Reuse existing packet kinds and blocker states wherever possible.
- Let FlowGuard/Reviewer results clear blockers through existing pass logic.

**Non-Goals:**

- No direct Controller blocker clearance.
- No PM authority to approve FlowGuard or Reviewer gates.
- No new break-glass transaction system.
- No compatibility shims for old result shapes or route plans.

## Decisions

1. Use `resolve-stopped-blocker` instead of a new top-level command.

   The user is resolving a stopped blocker, so the existing command is the
   smallest public surface. The new resolution name is explicit enough to avoid
   confusing it with PM reissue.

2. Reuse `awaiting_recheck`.

   `awaiting_recheck` is already a clearable semantic blocker status. A new
   status family would add lifecycle complexity without changing behavior.

3. Add only `pm_stop_previous_status` on the target packet.

   `stop_for_user` changes the repair target packet to `pm_stopped`. Recovery
   needs to restore the target to its prior routing status. Without preserving
   the previous status, older targets can remain unroutable after reattachment.

4. Force fresh recheck packets.

   Existing `_ensure_*` helpers intentionally reuse matching packets. Reattach
   must not reuse old accepted FlowGuard or Reviewer packets; it needs a fresh
   evidence/review chain tied to the repaired state.

5. Clear only after the existing owner gate passes.

   The reattach command issues the recheck packet and records recovery intent.
   It does not call `_clear_semantic_blockers_for_pass()` directly.

## Recheck Target Selection

- `gate_kind == "review"` or `required_recheck_role == "reviewer"`:
  issue a fresh Reviewer packet for the blocker subject.
- `gate_kind == "flowguard_check"` or `required_recheck_role == "flowguard_operator"`:
  issue a fresh FlowGuard packet for the blocker subject; normal pass flow then
  issues Reviewer review when needed.
- Other task/owner blockers stay on the existing PM repair path unless the
  existing runtime can identify a current task recheck owner.

For blocker-0005-class evidence-runner failures, reattachment should freshen
FlowGuard evidence first, then require Reviewer review before blocker clearance.

## Risks / Trade-offs

- If the underlying break-glass repair did not actually fix the evidence path,
  the fresh recheck packet will block again. That is expected and safer than
  direct clearance.
- Old runs without `pm_stop_previous_status` require a conservative fallback
  to `result_submitted` only when the packet has a target result and is
  currently `pm_stopped`.
