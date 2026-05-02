# Child Skill Contract Conformance Loop FlowGuard Findings

Date: 2026-04-30

## Scope

This process-preflight model tests how FlowPilot should verify that an invoked
child skill was actually used according to its own instructions before a parent
route node can advance.

FlowPilot owns orchestration: route state, heartbeat, evidence, transitions,
fallbacks, and completion closure. Child skills own domain execution details.
The modeled risk is that FlowPilot could claim "the UI skill was used" or "the
FlowGuard skill was used" while only performing a shallow subset of the child
skill's required workflow.

## Modeled Branches

The model includes two child-skill branches:

- a generic child-skill branch for non-UI skills;
- a UI child-skill branch for concept-led UI and visual implementation work.

The UI branch is intentionally explicit because it is where process shortcuts
are easiest to miss: concept target, visible target/reference, implementation
from target, rendered QA, divergence review, and visual iteration closure.

## Conformance Loop

Every child-skill invocation must pass this loop:

1. Select the source skill.
2. Read the source skill's `SKILL.md`.
3. Load relevant references or record skips with reasons.
4. Extract required workflow steps.
5. Map hard gates into the parent route.
6. Map the child skill's completion standard.
7. Write the child-skill evidence checklist.
8. Build and check a conformance model for this child-skill use.
9. Run layered review for child-skill risks.
10. Execute the mapped child-skill workflow.
11. Collect step-level evidence.
12. Audit that required steps have evidence.
13. Confirm evidence matches actual outputs.
14. Run domain-quality review against the parent goal.
15. Close the child-skill iteration loop.
16. Verify the child skill met its own completion standard.
17. Return control to the parent route node.

The parent node may not resume before step 16 passes.

## UI-Specific Checks

For UI child skills, the model requires:

- current UI/product state inspection before concept work;
- concept target or authoritative reference before implementation;
- visible and persisted target/reference evidence;
- implementation plan mapped from concept, interaction, and UI requirements;
- UI implementation from that target;
- rendered QA evidence after implementation;
- concept-vs-rendered divergence review;
- visual iteration decision and loop closure.

Rendered QA cannot be relabeled as pre-implementation concept evidence.

## Failure And Iteration Paths

The model includes two failure branches:

- required-step gap: the audit finds a missing or shallow child-skill step and
  routes back through child execution before parent resume;
- domain-quality gap: the quality review fails and routes back through the
  affected child-skill work, evidence collection, audit, and quality review.

This makes child-skill verification iterative instead of a single completion
checkbox.

## Check Results

Commands:

```powershell
python -m py_compile .flowpilot/task-models/child-skill-contract-conformance-loop/model.py .flowpilot/task-models/child-skill-contract-conformance-loop/run_checks.py
python .flowpilot/task-models/child-skill-contract-conformance-loop/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Result:

- states: 132;
- edges: 133;
- invariant failures: 0;
- missing required labels: 0;
- missing completed child-skill kinds: 0;
- progress findings: 0;
- stuck states: 0;
- non-terminating components: 0.

Representative success traces:

- generic child skill baseline: 22 heartbeat steps;
- UI child skill baseline: 29 heartbeat steps;
- UI child skill with required-step remediation: 40 heartbeat steps;
- UI child skill with quality iteration: 37 heartbeat steps.

Integrated controller checks after wiring the model into FlowPilot:

- meta model: 4226 states, 4823 edges, 0 invariant failures,
  0 missing labels, 0 stuck states;
- capability model: 304 states, 315 edges, 0 invariant failures,
  0 missing labels, 0 stuck states.

## Design Implication

FlowPilot should add a first-class child-skill conformance loop to its
capability architecture:

- child-skill use requires instruction loading, requirement extraction, and
  evidence planning before execution;
- child-skill use should be model-checked when it materially affects a formal
  route node;
- parent nodes cannot resume on a child-skill claim alone;
- evidence must be audited against actual outputs;
- domain quality must be checked against the parent node goal;
- failed child-skill audits route back into child-skill execution rather than
  allowing the parent route to continue.
