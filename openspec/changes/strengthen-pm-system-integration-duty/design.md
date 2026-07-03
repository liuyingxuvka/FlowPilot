## Context

FlowPilot already models a staged project-control process with PM-owned product architecture, route skeletons, node acceptance plans, PM result absorption, Reviewer backward replay, FlowGuard model checks, and terminal closure. The current weakness is not a missing role or a missing runtime gate. The weakness is that "system integration" is implied in several places but not carried as one continuous PM-owned thread.

The observed failure class is broader than fiction continuity. It applies to software, UI work, reports, research artifacts, and skill/workflow creation: every local block can appear complete, but the combined artifact can still be scattered, repetitive, under-bridged, incorrectly ordered, or structurally too flat.

Current constraints:

- FlowPilot is a current-contract runtime; do not add compatibility shims, legacy aliases, prose parsers, missing-field defaults, or alternate runtime acceptance paths.
- `node_context_package` is a fixed five-field worker starting context and must not be expanded for this change.
- Reviewer is not a second PM. Reviewer can block only when existing hard failure classes are met.
- FlowGuard reports support PM decisions and model/process repair; they do not mutate routes, approve gates, or replace PM judgement.
- The desired quality posture is high ceiling and low enough floor: optional 9/10 improvements are PM decision support unless the minimum current gate is actually unmet.

## Goals / Non-Goals

**Goals:**

- Make PM the explicit system integration owner from product architecture through final closure.
- Make FlowGuard model scattered local-pass/global-incoherence as a process risk.
- Make Reviewer challenge composition, continuity, structure, duplication, and missing bridges through existing parent/final replay.
- Preserve existing authority boundaries and current-contract runtime behavior.
- Add full-domain Cartesian coverage for both missed hard integration failures and overblocking advisory suggestions.
- Keep implementation scoped to prompt cards, templates, FlowGuard models, tests, OpenSpec records, install sync, topology, and version/git sync.

**Non-Goals:**

- Do not add a new runtime hard gate, self-stop, role, ledger, packet kind, route state family, or compatibility layer.
- Do not expand `node_context_package`.
- Do not promote every integration improvement into a hard blocker.
- Do not change the frozen acceptance contract rules, release/publish actions, or public runtime command interface.

## Decisions

### Decision 1: Integration duty is PM-owned, not a new role

Use existing PM artifacts as the single owner of system integration:

- product architecture records the root integration intent;
- route skeleton records composition across parent, sibling, producer, and consumer nodes;
- node acceptance plan records a node-local integration touchpoint outside `node_context_package`;
- PM result absorption checks whether a local result damages upstream/downstream composition;
- parent segment decision records whether children compose into the parent goal;
- final ledger and final backward replay judge the delivered artifact as one artifact;
- model-miss triage treats scattered local pass/global incoherence as a modelable miss.

Alternative considered: create a dedicated "system integrator" role. Rejected because PM already owns route, product architecture, and completion authority, and another role would create duplicate authority.

### Decision 2: Keep Reviewer and FlowGuard as challengers and evidence producers

Reviewer and FlowGuard cards will be strengthened to name the failure class, but their outputs remain classified through existing PM suggestion and blocker fields.

Advisory examples:

- shorter equivalent structure;
- cleaner section ordering;
- more elegant API shape;
- clearer foreshadowing or callback;
- optional duplicate removal where the current artifact is still usable.

Hard examples:

- explicit requirement unmet;
- missing proof for a user-facing claim;
- semantic downgrade;
- route cannot execute;
- producer-before-consumer inversion;
- required child outputs do not compose into the parent goal;
- final delivered artifact fails root intent.

Alternative considered: make integration review a new minimum hard blocker. Rejected because it would raise the floor too far and make ordinary FlowPilot runs brittle.

### Decision 3: Add integration touchpoints outside current worker package contracts

The node acceptance plan template may gain an outer `integration_touchpoint` section, but the inner `node_context_package` remains exactly the current five-field starting context. The worker still executes the bounded packet; PM and Reviewer own the cross-node relation.

Alternative considered: add integration fields into the node context package. Rejected because current discipline explicitly forbids expanding that package for PM-only planning metadata.

### Decision 4: Model and test the finite domain instead of relying on prose

The new coverage must be Cartesian and model-scoped. The axes will cover stage, role, artifact family, failure class, severity, authority, evidence timing, and expected outcome. The matrix must include two directions:

- underblocking: hard integration failure is incorrectly passed;
- overblocking: advisory integration improvement is incorrectly made a hard blocker.

Alternative considered: add a handful of focused prompt tests. Rejected because this would not cover role, stage, severity, and outcome interactions.

## Risks / Trade-offs

- Integration language could become vague prompt prose -> Mitigation: add explicit template keys, card phrase tests, FlowGuard hazards, and Cartesian matrix cases.
- Reviewer could overblock quality suggestions -> Mitigation: test advisory suggestions that must remain PM decision support.
- PM could ignore hard composition failures as optional -> Mitigation: test hard composition failures that must route to repair, route mutation, terminal block, or model-miss triage.
- FlowGuard model scope could become too broad -> Mitigation: keep the model scoped to process states and finite declared axes; do not claim universal semantic truth.
- Background regressions could be mistaken for completion while still running -> Mitigation: use the repository background log contract and inspect exit artifacts before final claims.

## Migration Plan

1. Create OpenSpec artifacts for the integration-duty change.
2. Update runtime-kit PM, Reviewer, FlowGuard, Worker, phase, parent replay, final replay, and model-miss cards.
3. Update reusable templates without changing runtime contracts or `node_context_package`.
4. Update FlowGuard planning-quality and related simulation models.
5. Add Cartesian coverage, fake-AI replay coverage, prompt/card phrase coverage, and TestMesh/MTA bindings.
6. Run focused tests first, then model regressions, then install sync/audit/check.
7. Rebuild and check FlowGuard project topology after model/test/card changes.
8. Commit the scoped work only after validation evidence is current.

Rollback is ordinary source rollback of this OpenSpec change and the touched prompt/template/model/test files. No runtime migration or data migration is introduced.
