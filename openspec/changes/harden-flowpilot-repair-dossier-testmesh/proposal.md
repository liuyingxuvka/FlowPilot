## Why

The June 28 FlowPilot run showed that the repair path can loop for dozens of
same-parent repair nodes because repair context is fragmented across packet
families. PM packets may see some blocker bodies, worker packets may receive
zero repair-context reads, reviewer packets may see only the current PM plan,
and the glass-break counter can forget superseded blockers.

FlowPilot needs one current-contract repair information path that preserves
sealed-body role boundaries during normal work, but automatically shares the
complete current repair-chain context with the roles that must repair or
recheck the same blocker lineage.

## What Changes

- Introduce a runtime-owned repair dossier for active blocker repair lineages.
  The dossier records the base node, parent scope, blocker chain, blocked
  packets/results, PM decisions, repair packets, review results, unresolved
  obligations, repair depth, and normal-recovery status.
- Replace packet-family-specific repair authorization assembly with one
  current repair-context authorization policy. Normal packets keep minimal
  reads; packets inside a repair dossier receive role-scoped repair-chain
  context.
- Mark inherited prior bodies as context-only unless they are the current
  packet's new evidence. Old bodies can explain what happened but cannot close
  the current repair obligation.
- Harden blocker routing so fixed next-action rules are enforced mechanically.
  Missing required information must reissue with materials when runtime can
  authorize them, or stop/control-block when it cannot; it must not become an
  ordinary route-repair loop.
- Align Reviewer and FlowGuard packet subjects with current-stage evidence.
  PM node-context plans are plan-stage artifacts, not repaired worker evidence
  or repair closure evidence. They remain reviewable as plans when the
  `review_window` says the current subject is `node_plan_definition`.
- Simplify glass-break to same-parent repair progress: five consecutive repair
  nodes in the same dossier without recovery to a normal non-repair business
  node must enter Controller break-glass.
- Add a generated Cartesian TestMesh covering role, packet family, blocker
  class, repair depth, authorization state, evidence state, and recovery state,
  plus observed-run replay for the June 28 repair loop.
- Sync the repository-owned FlowPilot skill to the installed local Codex skill
  only after source validation passes, then audit the installed copy against
  source content.

## Capabilities

### New Capabilities

- `repair-dossier-context`: Runtime-owned active repair lineage context,
  role-scoped authorization, context-only evidence labels, and normal-recovery
  tracking.
- `repair-cartesian-testmesh`: Generated validation matrix and parent/child
  evidence policy for repair dossier authorization, blocker routing,
  reviewer/FlowGuard subject alignment, and observed-loop replay.

### Modified Capabilities

- `blocker-repair-policy`: Enforce fixed blocker-class next actions and
  prohibit ordinary repair for material-authorization blockers.
- `controller-break-glass-repair`: Simplify threshold behavior to five
  consecutive same-parent repair nodes without normal recovery.
- `flowpilot-packet-review-flow`: Ensure reviewer packets receive the repair
  dossier context needed to recheck the current blocker lineage without using
  old bodies as current evidence.
- `flowguard-boundary-test-alignment`: Bind repair dossier obligations,
  current evidence subjects, and Cartesian coverage cells to executable model
  and unit test evidence.

## Impact

- Runtime repair and packet issuing logic under
  `skills/flowpilot/assets/flowpilot_core_runtime/`.
- Runtime cards for PM repair decisions, PM node acceptance plans, worker
  packets, FlowGuard operator checks, reviewer checks, and Controller
  break-glass.
- FlowGuard simulation/model checks for blocker repair information flow,
  project-control information flow, break-glass, and repair TestMesh coverage.
- Unit tests and synthetic replay tests under `tests/` and `simulations/`.
- Install/sync validation through `scripts/install_flowpilot.py`,
  `scripts/audit_local_install_sync.py`, and `scripts/check_install.py`.
