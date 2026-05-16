## Context

`confirm_controller_core_boundary` was added to prevent Controller from
operating without a recorded authority boundary. That boundary is valid and
should remain. The problem is that the boundary is now presented as a separate
foreground Controller task during startup, even though the boundary text and
allowed rules are already part of `load_controller_core`.

## Goals / Non-Goals

**Goals:**

- Make `load_controller_core` own the fresh startup boundary confirmation
  postcondition.
- Keep a durable `startup/controller_boundary_confirmation.json` artifact and
  matching Router/runtime receipt evidence.
- Let startup pre-review reconciliation depend on the artifact and flags, not
  on a separate visible Controller row.
- Keep old pending/completed `confirm_controller_core_boundary` rows
  reconcilable for existing runs.
- Prove the behavior with FlowGuard and focused runtime tests before syncing
  the installed skill.

**Non-Goals:**

- Do not remove the boundary confirmation artifact.
- Do not let Controller approve gates, mutate route state, read sealed bodies,
  or perform PM/Worker/Reviewer work.
- Do not change startup intake schemas, role output envelope schemas, or public
  release behavior.

## Decisions

1. `load_controller_core` becomes the single fresh-start owner.
   - It can complete only after Router records Controller core readiness and
     boundary confirmation evidence.
   - It may reuse the existing confirmation body/receipt helpers so evidence
     stays canonical.

2. `confirm_controller_core_boundary` remains a compatibility action.
   - If an old run already has the action, Router still accepts its valid
     runtime evidence.
   - The scheduler must not create a new fresh-run row after
     `load_controller_core` has satisfied the boundary postcondition.

3. Reconciliation is fact-based.
   - Pre-review and startup obligation checks look for the confirmation
     artifact, receipt, and Router flags.
   - They do not block merely because the standalone boundary action was never
     queued.

## Risk Catalog

| Risk ID | Possible bug | Guard |
| --- | --- | --- |
| R1 | Boundary artifact is skipped while the action row disappears | FlowGuard requires `controller_role_confirmed` only with valid artifact/receipt evidence |
| R2 | Fresh startup still queues `confirm_controller_core_boundary` | FlowGuard and runtime tests reject the redundant row after core load |
| R3 | Existing runs with pending boundary rows stop reconciling | Compatibility test keeps the action path valid |
| R4 | Controller boundary rules are weakened | Tests assert the boundary record still preserves the forbidden capabilities |
| R5 | Startup review waits for an action row instead of evidence | Reconciliation tests check artifact/flag-based readiness |

## Migration Plan

1. Add/update a focused FlowGuard startup-control scenario for core-load-owned
   boundary confirmation.
2. Update runtime reconciliation so successful `load_controller_core` writes or
   reconciles the canonical boundary confirmation evidence.
3. Stop fresh startup scheduling from emitting a new
   `confirm_controller_core_boundary` row after that evidence is present.
4. Keep the existing explicit action handler for old runs.
5. Run focused tests, then background Meta/Capability regressions.
6. Sync the installed local FlowPilot skill and audit the install.
