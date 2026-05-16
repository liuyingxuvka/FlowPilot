## Context

The existing blocker repair policy table already separates mechanical
control-plane reissues from semantic PM repair. The observed failure is that a
Controller action marked `done` can fail Router postcondition reconciliation
and then be classified through the PM-default path, even though the recovery is
usually the same mechanical deliverable retry used by the Controller
postcondition contract.

This change is a narrow policy/classifier correction. It does not introduce a
new blocker workflow.

## Goals / Non-Goals

**Goals:**

- Route missing Router postconditions from Controller receipts through the
  existing mechanical reissue policy before PM escalation.
- Preserve bounded retry behavior: two direct repair chances, then PM.
- Keep PM routing for semantic, route-changing, fatal, and self-interrogation
  blockers.
- Keep blocker metadata internally consistent so live projections do not show
  "zero retry budget but not exhausted" as an available local retry.

**Non-Goals:**

- Do not rebuild the blocker policy table or add a second repair mechanism.
- Do not change sealed body boundaries or Controller authority.
- Do not run heavyweight Meta/Capability simulations for this focused fix.
- Do not convert valid stopped-by-user history into normal completion.

## Decisions

1. Classify by source before falling back to semantic PM repair.

   `controller_action_receipt_missing_router_postcondition` is a specific
   reconciliation source, not a free-form PM semantic failure. The classifier
   should map it to `control_plane_reissue` while the direct retry budget is
   available.

2. Use the existing mechanical policy row.

   The row `mechanical_control_plane_reissue` already has
   `first_handler=responsible_role`, `direct_retry_budget=2`, and PM
   escalation. Reusing it keeps the repair small and prevents a new policy
   surface.

3. Prefer the Controller as the responsible role for this source.

   When a postcondition is missing after a Controller receipt, the immediate
   repair is to complete or reissue the Controller deliverable evidence. If no
   responsible role is provided by the event, Router should not default this
   source to PM before the direct retry budget is spent.

4. Normalize budget exhaustion independent of first handler.

   A zero direct retry budget means no direct retries are available. PM-first
   blockers can still be PM-first, but their metadata should not imply that a
   direct retry is pending.

## Risks / Trade-offs

- Over-classifying postcondition misses as mechanical could hide a semantic
  failure -> Keep the mapping limited to the named reconciliation source and
  preserve PM escalation after bounded retries or invalid evidence.
- Responsible-role fallback could send unrelated blockers to Controller -> Only
  apply Controller fallback for the named postcondition source.
- Historical stopped runs still contain old blocker artifacts -> Report them as
  historical projection warnings, not proof that the repaired runtime still
  misroutes new blockers.

## Migration Plan

1. Extend the focused FlowGuard process/daemon checks with the expected blocker
   lane behavior.
2. Patch Router classifier and responsible-role fallback for the named source.
3. Add focused runtime tests for first issue, retry attempts, and PM escalation.
4. Run focused tests, OpenSpec validation, install sync/audit, and lightweight
   FlowGuard checks. Record skipped Meta/Capability models by user direction.
