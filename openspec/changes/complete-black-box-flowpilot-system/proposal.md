## Why

The current repository now has a clean black-box runtime foundation, but it is
not yet a complete FlowPilot replacement: it does not provide the full startup
surface, dynamic live-agent host loop, FlowGuard officer workflow, Cockpit
operation surface, long-run recovery, migration/cutover path, or real project
validation needed for a full-system completion claim.

This change turns the foundation into a complete, production-capable FlowPilot
system while preserving the core boundary learned from prior failures: the
current-run ledger is authority, and old runtime state, chat memory, stale
artifacts, fixed role topology, and compatibility aliases are reference
material only.

## What Changes

- Add a complete black-box FlowPilot system contract that covers startup,
  run-scoped ledger persistence, dynamic responsibility leases, real host-agent
  integration, sealed packets/results, FlowGuard work-order scheduling, review
  gates, route mutation, final backward closure, Cockpit/status operation, and
  migration/cutover.
- Extend the clean runtime from deterministic scenario support into a full
  project-control runtime with explicit states, events, artifacts, APIs, and
  failure branches.
- Add model-first development, UI, code-structure, model-test, and TestMesh
  gates before broad implementation or completion confidence.
- Add fake-agent, historical-bad-case, chaos, and real live-run validation
  requirements. Scoped green checks remain scoped; they do not satisfy full
  completion without matching live/host evidence.
- Keep old FlowPilot assets as a source library only: startup panel ideas,
  icon assets, envelope field names, route-sign display logic, install scripts,
  and historical failure cases may be reused when mapped to the new ledger.
- **BREAKING**: Old `.flowpilot` control state, fixed named-agent startup as a
  runtime invariant, old agent ids, stale result artifacts, and compatibility
  aliases cannot act as current authority for the complete system.

## Capabilities

### New Capabilities

- `complete-black-box-flowpilot-system`: Full-system FlowPilot contract covering
  current-run authority, dynamic leases, host integration, Cockpit/status
  operation, FlowGuard work-order routing, review/repair/final closure,
  migration/cutover, and full validation evidence.

### Modified Capabilities

- `flowpilot-maintenance-ideal-state`: Full completion claims must distinguish
  the existing clean runtime foundation from the future complete system and
  require live host, UI, migration, and full validation evidence.
- `interactive-startup-intake`: Startup intake becomes one part of the complete
  black-box run shell and must produce sealed current-run evidence compatible
  with the new ledger.
- `runtime-ledger-persistence`: Current-run ledger persistence must cover the
  complete runtime surface, not only the existing router/control surfaces.
- `multiround-fake-ai-control-rehearsal`: Fake-agent rehearsal must expand from
  protocol stress testing to the full-system bad-case matrix.
- `historical-live-run-replay-package-suite`: Historical replay becomes a hard
  full-system confidence gate, not an optional regression note.

## Impact

- New OpenSpec artifacts under
  `openspec/changes/complete-black-box-flowpilot-system/`.
- New or extended FlowGuard models and runners under `simulations/`.
- New or extended runtime modules under
  `skills/flowpilot/assets/ai_project_runtime/`, with selective reuse from
  existing FlowPilot assets only through explicit adapters.
- New tests under `tests/` for full-system runtime states, dynamic host
  behavior, Cockpit/status projection, FlowGuard order routing, validation
  evidence, and migration/cutover.
- Install inventory, version, changelog, local installed skill sync, and local
  git history will be updated before any completion claim.
