## Why

Heartbeat and manual resume restore the current run and the six background
roles, but they still default to asking PM for the next resume decision before
Router checks whether current-run ledgers already prove the next mechanical
step. Mid-run role recovery already has the safer and faster behavior: after a
role is restored, Router scans outstanding obligations, settles valid existing
evidence, reissues missing work, and escalates to PM only for ambiguity.

## What Changes

- Add a shared post-rehydration obligation replay step for heartbeat/manual
  resume after `rehydrate_role_agents` succeeds.
- Reuse the existing role-recovery obligation replay planner for current-run
  metadata-only checks instead of adding a second comparison mechanism.
- Keep daemon attach, stable launcher, visible plan restore, and six-role
  liveness checks in the heartbeat/manual resume path.
- Preserve the existing mid-run role liveness recovery path and its targeted
  recovery behavior.
- Ask PM after resume only when replay finds semantic ambiguity, route or
  acceptance drift, conflicting outputs, unresolved packet ownership, missing
  memory/context, or no legal mechanical continuation.

## Capabilities

### New Capabilities

- `resume-rehydration-obligation-replay`: Heartbeat/manual resume reuses
  Router-owned obligation replay after six-role rehydration.

### Modified Capabilities

- `role-recovery-obligation-replay`: Existing role recovery replay remains the
  shared metadata-only reconciliation mechanism for restored or replaced roles.

## Impact

- Affected implementation: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected models/checks: resume and role-recovery FlowGuard models.
- Affected tests: focused router runtime resume/recovery tests.
- Affected local distribution: repo-owned FlowPilot skill must be synced into
  the local installed skill after validation.
- Explicitly skipped by user request: heavyweight Meta and Capability model
  simulations for this pass.
