## Context

The current new runtime owns a clean black-box ledger, sealed packets, dynamic
leases, FlowGuard work-order packets, independent review, validation, recursive
route nodes, PM disposition, and final route-wide closure. The remaining gap is
not the old UI or the old six-role topology. The gap is the set of control
gates that prevent low-standard completion:

- PM must raise the request into a highest-reasonable current standard.
- PM must plan from current material and installed skill facts.
- selected skills must create evidence obligations.
- every node must be acceptance-planned before work starts.
- failed nodes should usually deepen/repair in place.
- parent nodes must compose child outcomes backward.
- final closure must prove requirements, not just packet completion.

## Goals / Non-Goals

**Goals:**

- Add the smallest runtime-level gate set that restores those necessary old
  capabilities without resurrecting the old router.
- Keep every gate represented as current-run ledger state and packet evidence.
- Make route planning illegal until pre-planning gates are accepted.
- Make node execution illegal until the active node has an accepted acceptance
  plan.
- Make final closure illegal until the requirement-evidence matrix is clean.
- Extend FlowGuard and ordinary tests for good path and bad path coverage.

**Non-Goals:**

- Do not restore the fixed six-agent topology as a hard runtime invariant.
- Do not make Cockpit or any monitor UI required.
- Do not use old router state as authority.
- Do not copy the full old card stack into the new runtime.
- Do not treat raw material maps, raw skill inventory, or role prose as
  acceptance evidence by themselves.

## Decisions

### Decision: Use packet families instead of old phase cards

The new runtime will introduce first-class packet kinds for:

- `high_standard_contract`
- `discovery`
- `skill_standard`
- `node_acceptance_plan`
- `parent_backward_replay`
- `requirement_evidence_matrix`

Each is still a sealed packet/result loop with the existing FlowGuard, review,
validation, and closure behavior where appropriate. This keeps the runtime
small and symmetric while making the gates explicit.

Alternative considered: re-enable the old runtime-kit cards as the active
state machine. That would bring back the complexity we are intentionally
removing.

### Decision: Planning is blocked by accepted pre-planning gates

The initial PM planning packet remains, but it is only legal after the runtime
has accepted:

- the PM high-standard contract;
- material discovery;
- local skill inventory;
- the PM skill standard selection.

This prevents PM route planning from being based only on the startup body or
memory.

### Decision: Node execution is blocked by node acceptance planning

Before issuing a task packet for an active route node, the runtime ensures a
node acceptance plan packet exists and is accepted. The plan binds the active
node to:

- high-standard requirement ids;
- acceptance criteria;
- skill standard obligation ids;
- proof/evidence obligations;
- low-quality-success risks;
- repair policy.

The worker packet then includes the accepted plan id.

### Decision: Same-node repair is the default PM disposition

PM disposition values keep the existing set, but the runtime distinguishes:

- `repair`: same-node repair/deepening, keeping the current node active;
- `mutate_route`: route rewrite or new repair node;
- `block`/`stop`: controlled nonterminal stop;
- `accept`: advance only when the node has current accepted evidence.

This makes route mutation a deliberate structural decision rather than the
default response to ordinary quality gaps.

### Decision: Parent backward replay is conditional on child structure

Parent/module nodes with children cannot close from child acceptance alone.
They need an accepted parent backward replay packet or an explicit current-run
waiver before PM can accept the parent node.

### Decision: Final closure consumes a requirement-evidence matrix

The final route-wide ledger remains necessary, but it is not enough. Closure
also requires a clean requirement-evidence matrix that traces startup intent,
PM high-standard requirements, route nodes, skill standards, FlowGuard work,
reviews, validations, and PM dispositions.

## Risks / Trade-offs

- Adding gates can make simple tasks feel heavy -> keep discovery and skill
  standard packets compact and deterministic in fake rehearsal; future work can
  add task-size waivers with evidence.
- PM can over-expand scope -> classify high standards as hard current,
  current improvement, future suggestion, or rejected; only hard current rows
  block closure.
- Skill inventory can become raw authority -> raw availability only feeds PM
  selection; selected skills need evidence obligations before they matter.
- Parent replay can overcomplicate flat routes -> require it only when the
  route node declares children.
- Green tests can overclaim live quality -> keep fake rehearsals, FlowGuard
  hazards, model-test alignment, and local install checks separate.

## Migration Plan

1. Extend OpenSpec specs and task checklist.
2. Extend the recursive FlowGuard model with the high-standard gates and
   bad-case hazards.
3. Extend runtime ledger schema, router actions, packet side effects, closure
   blockers, run-shell projections, and fake-host rehearsal.
4. Add focused unit tests for pre-planning gates, node acceptance gates,
   same-node repair, parent replay, and final requirement matrix.
5. Run OpenSpec validation, FlowGuard checks, focused tests, fake rehearsal,
   install audit, and background heavyweight checks.
6. Sync the local installed skill and version evidence.

Rollback strategy: the change is isolated to the new black-box runtime path.
If validation fails, keep the OpenSpec change active and do not claim the local
installed FlowPilot version as upgraded.
