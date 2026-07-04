## 1. Runtime Gate Ownership

- [x] 1.1 Add a single current-node entry-gate helper that returns missing/open/stale node plan and context causes for the selected node itself.
- [x] 1.2 Update frontier advancement so a selected parent/module remains active and opens its own node-acceptance-plan packet before child descent.
- [x] 1.3 Update nonworker parent/module entry so child descent is impossible until the parent/module has its own current accepted plan and context.
- [x] 1.4 Add assertion-only handling at parent replay and PM disposition for missing parent entry gates, returning `control_plane_hard_gate_escape` without backfill.

## 2. Final Preflight Return Path

- [x] 2.1 Add a thin final-dispatch hard-gate preflight that classifies missing node entry, parent replay, PM disposition, stale evidence, and unresolved current packet leaks, while preserving existing accepted-packet and terminal-owner repair paths.
- [x] 2.2 Route each `control_plane_hard_gate_escape:<gate_type>:<subject_id>` back to its owning normal gate and freeze final Reviewer dispatch.
- [x] 2.3 Preserve clean final dispatch so Reviewer receives only delivered-output and route-composition quality review packets after hard-gate preflight passes.

## 3. Runtime Cards And Contracts

- [x] 3.1 Update PM node-acceptance and route-model cards to state that parent/module nodes are active nodes with their own entry gate before child execution.
- [x] 3.2 Update parent backward replay, PM segment decision, closure, and Reviewer cards to keep late hard-gate detection as runtime escape and final review as quality/composition review.
- [x] 3.3 Update packet/stage evidence metadata only where existing families need owner-gate visibility; do not add fallback result fields.

## 4. FlowGuard Model And Alignment

- [x] 4.1 Update the recursive closure/parent-entry model with the forbidden transition `parent selected -> child execution` before parent entry gate.
- [x] 4.2 Update the control-plane friction/canary model with hard-gate escape return-to-owner transitions.
- [x] 4.3 Update model-test alignment rows so parent-entry and final-dispatch return-path obligations bind to the new focused tests.

## 5. Cartesian And Regression Tests

- [x] 5.1 Add focused runtime tests for direct parent entry, later parent entry, corrupted `awaiting_children` parent recovery, child-plan-cannot-substitute, and parent late-assertion cases.
- [x] 5.2 Add final-preflight return-path tests for node entry, parent replay, PM disposition, stale evidence, unresolved packet, parent-order replay gap, and clean final quality dispatch.
- [x] 5.3 Add a Cartesian fake-AI replay matrix across hard-gate type, affected topology, detection stage, and owner-gate outcome, with scoped-out behavior explicit in matrix cells.
- [x] 5.4 Add fake-AI replay tests proving fake child success or final-review readiness cannot skip parent entry or hard-gate return.

## 6. Verification, Sync, And Git Hygiene

- [x] 6.1 Run focused runtime, fake-E2E, card, model, model-test alignment, and syntax checks from the verification contract.
- [x] 6.2 Run router/test-tier background checks where practical and inspect final artifact exit files before using them as evidence.
- [x] 6.3 Run topology build/check because model, tests, cards, and runtime surfaces changed.
- [x] 6.4 Run repository install checks, sync the source FlowPilot skill to the installed Codex skill, and verify source/installed digest equality.
- [x] 6.5 Review git status to stage only this change's source, tests, OpenSpec, and generated evidence files; leave unrelated peer-agent files untouched.
