## Context

FlowPilot has accumulated two kinds of assets:

- hard-won protocol knowledge about startup, packets, role authority,
  FlowGuard gates, review, route mutation, final closure, installation, and
  live-run failure modes;
- historical implementation weight in the old router/control-plane surfaces.

The recent clean runtime under `skills/flowpilot/assets/ai_project_runtime/`
proved a small core: ledger authority, dynamic leases, sealed packets,
FlowGuard work-order routing, independent review, final backward closure, and
safe console projection. That core is useful, but it is not the complete
system. A complete FlowPilot replacement also needs a real run shell, native
startup intake, Cockpit/status operation, host-agent leases, route mutation,
resume/recovery, validation evidence hierarchy, historical replay, live-run
trials, migration, install sync, and final cutover gates.

This design extends the clean runtime into the complete system without making
the old runtime authoritative. Old assets may be imported only through explicit
reference adapters or tests.

## Goals / Non-Goals

**Goals:**

- Make the current-run ledger the single authority for all full-system state.
- Replace fixed permanent role topology with dynamic responsibility leases.
- Provide deterministic router decisions for startup, route drafting, packet
  execution, FlowGuard work orders, review, repair, route mutation, resume,
  Cockpit/status projection, and final closure.
- Route FlowGuard automatically by the modeled target, not by whichever agent
  asks for help.
- Add Cockpit/status surfaces that are projections over the ledger and never
  become alternate authorities.
- Add fake-agent, historical replay, chaos, and real live-run gates before a
  broad full-completion claim.
- Preserve existing old FlowPilot assets only as reusable source material,
  negative tests, or migration inputs.

**Non-Goals:**

- This change does not push, tag, publish, or deploy.
- This change does not delete historical FlowPilot files as its first step.
- This change does not treat old `.flowpilot` state, chat memory, old agent
  ids, or stale result artifacts as current authority.
- This change does not require a fixed six-agent runtime invariant. Six named
  roles may remain a default presentation/compatibility vocabulary, but the
  runtime authority is the current lease and responsibility record.
- This change does not claim full completion from deterministic fake-agent
  checks alone.

## Decisions

### Decision: Current-run ledger is the authority

The complete system keeps top-level `.flowpilot/current.json` and
`.flowpilot/index.json` as pointers/catalogs only. Every active run writes a
fresh `.flowpilot/runs/<run-id>/` shell. The complete runtime state lives under
that run root:

- `ledger.json` for canonical state;
- `events.jsonl` for append-only event history;
- `routes/` for route versions and route mutation records;
- `packets/envelopes/` and `packets/bodies/` for sealed task packets;
- `results/envelopes/` and `results/bodies/` for sealed result packets;
- `leases/` for current responsibility leases;
- `flowguard/work_orders/` for modeled-target work orders and reports;
- `reviews/` for independent review reports;
- `evidence/` for validation and proof-artifact references;
- `console/status.json` for public projection;
- `closure/` for final backward chain evidence.

Alternative considered: keep the old router state as the canonical authority
and add new status fields. That preserves too many old compatibility paths and
makes stale evidence hard to reject.

### Decision: Router is deterministic software; agents are leased workers

The router reads the ledger and emits a typed next action. It does not do
project work, approve gates, or read sealed bodies. Agent work happens through
leases. A lease has one responsibility, a run id, a route scope, allowed
actions, liveness records, expiration, and an output contract. A closed,
expired, or superseded lease cannot produce authoritative output.

Alternative considered: keep permanent role agents as the state model. That is
too fragile when background agents disappear, duplicate, resume with stale ids,
or submit late outputs.

### Decision: FlowGuard is scheduled by modeled target

Every FlowGuard request records `modeled_target` before work starts. The
scheduler maps it to the selected FlowGuard skill. A green report for the
wrong target does not satisfy the gate.

Target examples:

- `development_process` -> `flowguard-development-process-flow`
- `ui_interaction_flow` -> `flowguard-ui-flow-structure`
- `code_structure_plan` -> `flowguard-code-structure-recommendation`
- `test_and_evidence_hierarchy` -> `flowguard-test-mesh`
- `model_test_alignment` -> `flowguard-model-test-alignment`
- `model_miss` -> `flowguard-model-miss-review`
- `architecture_reduction` -> `flowguard-architecture-reduction`

Alternative considered: let PM or Controller choose arbitrary skill names in
free text. That repeats prior prompt-coverage failures where green checks did
not model the needed target.

### Decision: Cockpit is a projection, not an authority

The first Cockpit implementation is intentionally operational rather than
decorative. It renders project status, route stage, packets, leases,
FlowGuard orders, blockers, validation rows, and closure status from public
ledger projection data. It may submit user events such as pause, resume, stop,
open logs, or request details. It may not edit canonical state directly and it
must not expose sealed packet or result bodies.

Alternative considered: reuse old UI/router state directly. That would make
display projection conflict with router authority again.

### Decision: Testing is hierarchical

Routine checks prove the code surface; release/full-system gates prove the
broader claim. The full gate consumes:

- OpenSpec validation;
- FlowGuard development-process, UI-flow, code-structure, model-test, and
  TestMesh reports;
- focused unit tests;
- fake-agent multiround and chaos scenarios;
- historical bad-case replay;
- install sync/audit/check;
- background Meta/Capability regressions with inspected artifacts;
- at least one real host-agent live run before live confidence can be claimed;
- final backward closure over current evidence.

Alternative considered: use existing small runtime scenarios as release
evidence. That is scoped evidence and would overclaim.

## Risks / Trade-offs

- Full-system scope is large -> Build and validate in layers, but keep the
  final OpenSpec contract broad so a small slice cannot be mistaken for
  completion.
- Existing old router still exists -> Use explicit adapters and tests; do not
  import old state as current authority.
- Real host-agent integration may be environment-dependent -> Make host
  drivers pluggable and distinguish fake-host, dry-run, and live-host evidence.
- Cockpit may lag runtime behavior -> Treat UI as a projection with
  model-backed UI-flow tests and browser/manual evidence before UI completion.
- Background checks can be progress-only -> Require exit artifacts and proof
  artifact references before release confidence.
- Multiple OpenSpec changes are active -> Keep this change additive and scoped
  to the complete-system rebuild. Do not silently finish unrelated cleanup
  work as part of this contract.

## Migration Plan

1. Keep the existing old FlowPilot runtime and the clean small runtime in place.
2. Add the complete-system OpenSpec contract and FlowGuard development models.
3. Extend `ai_project_runtime` with complete-system state, router, host,
   Cockpit/status, migration, and validation modules.
4. Add fake-host and chaos tests until full deterministic coverage is current.
5. Add adapters that can import old outputs only as read-only evidence.
6. Add install inventory and local install sync.
7. Run routine, background, install, historical replay, and live-host checks.
8. Only after full evidence is current, mark the new runtime as the preferred
   FlowPilot implementation path. Old runtime remains reference/diagnostic
   material until a separate removal change.

Rollback strategy: preserve the previous committed FlowPilot skill and keep the
old runtime callable until the final cutover gate passes. If full-system
validation fails, the new runtime remains experimental/scoped and cannot
replace the current public entrypoint.

## Open Questions

- Which host APIs are available for true live background-agent spawn in every
  target environment? Until proven, live-host evidence remains scoped to the
  current machine.
- How much of Cockpit should be native desktop versus browser UI? The initial
  contract requires a usable status/control surface, not final visual design.
- Which historical live-run packages are mandatory for the first cutover? The
  initial set should include ACK-only completion, stale display projection,
  stale unowned package disposition, wrong FlowGuard target, dead worker
  replacement, and progress-only background evidence.
