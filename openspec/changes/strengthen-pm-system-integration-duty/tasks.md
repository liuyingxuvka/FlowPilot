## 1. Preflight And Ownership Grounding

- [x] 1.1 Verify real FlowGuard import, package version, and project audit status before implementation.
- [x] 1.2 Inspect existing PM, Reviewer, FlowGuard operator, Worker, phase, parent replay, final replay, and model-miss cards for integration ownership surfaces.
- [x] 1.3 Inspect planning-quality, Cartesian, ContractExhaustionMesh, TestMesh, fake-AI replay, meta, and capability model/test surfaces for existing coverage.
- [x] 1.4 Record the FlowGuard route decision: ExistingModelPreflight plus DevelopmentProcessFlow, ContractExhaustionMesh, TestMesh, and Model-Test Alignment for coverage.

## 2. Prompt Card Upgrades

- [x] 2.1 Update the PM role card to name PM as system integration owner without adding runtime authority or a new role.
- [x] 2.2 Update the Reviewer role card to challenge composition, continuity, duplication, and structure while keeping advisory findings as PM decision support.
- [x] 2.3 Update the FlowGuard operator role card to model scattered local-pass/global-incoherence as process/model risk for PM.
- [x] 2.4 Update the Worker role card to keep Worker bounded to the current packet and avoid making Worker the system integrator.
- [x] 2.5 Update PM product architecture phase card with root system integration intent.
- [x] 2.6 Update PM route skeleton phase card with parent/child/sibling composition review.
- [x] 2.7 Update FlowGuard route process check card with route-level scattered-output risk modeling.
- [x] 2.8 Update PM node acceptance plan phase card with plan-level integration touchpoints outside `node_context_package`.
- [x] 2.9 Update Reviewer node acceptance plan review card to review integration touchpoints and classify hard vs advisory findings.
- [x] 2.10 Update PM current node loop card so PM result absorption checks upstream, downstream, sibling, and parent contribution effects.
- [x] 2.11 Update parent backward replay card to reject child-local passes that do not compose into the parent goal.
- [x] 2.12 Update PM parent segment decision card to record composition impact in existing decisions.
- [x] 2.13 Update final ledger and final backward replay cards with whole-output composition review from the delivered artifact.
- [x] 2.14 Update PM model-miss triage card with scattered local-pass/global-incoherence as a same-class model miss.

## 3. Template Upgrades

- [x] 3.1 Add `system_integration_intent` to the product function architecture template.
- [x] 3.2 Extend route template `structure_convergence_review` with parent/child/sibling composition fields.
- [x] 3.3 Add plan-level `integration_touchpoint` to the node acceptance plan template while preserving the exact five-field `node_context_package`.
- [x] 3.4 Extend final route-wide gate ledger template with whole-output composition review.
- [x] 3.5 Add tests that prove the templates expose integration fields and do not expand `node_context_package`.

## 4. FlowGuard Model Upgrades

- [x] 4.1 Add planning-quality state and hazards for missing system integration intent, route composition review, node integration touchpoint, PM absorption integration check, parent scattered-child pass, final node-only closure, and model-miss omission.
- [x] 4.2 Update the planning-quality runner expectations and result artifact shape only as needed for current model output.
- [x] 4.3 Update meta/capability model states or invariants only where they need to represent the PM integration thread at parent/final closure.
- [x] 4.4 Keep FlowGuard changes model-scoped and avoid claiming universal semantic truth outside declared obligations.

## 5. Full-Domain Cartesian Coverage

- [x] 5.1 Create a dedicated integration Cartesian coverage model with finite axes for stage, role, artifact family, failure class, severity, authority, evidence timing, and expected outcome.
- [x] 5.2 Generate underblocking cases where hard parent/final composition failures must not pass as advisory.
- [x] 5.3 Generate overblocking cases where optional concision, optional duplicate reduction, or higher-quality structure suggestions must not become runtime hard blockers.
- [x] 5.4 Include worker-boundary cases proving Worker remains a bounded executor and integration judgement stays with PM/Reviewer/FlowGuard.
- [x] 5.5 Add pytest coverage for the integration Cartesian matrix and required axis completeness.
- [x] 5.6 Update existing current-contract Cartesian tests where the new integration authority boundary must be visible.
- [x] 5.7 Update ContractExhaustionMesh coverage so generated integration case ids can be consumed by downstream TestMesh/MTA evidence.
- [x] 5.8 Update acceptance TestMesh and Model-Test Alignment coverage so the integration case ids have test ownership and obligation binding.

## 6. Fake-AI And Prompt Coverage Tests

- [x] 6.1 Add card instruction coverage assertions for PM system integration ownership, scattered local-pass defects, advisory-vs-hard classification, fixed `node_context_package`, and no runtime hard blocker language.
- [x] 6.2 Extend fake-AI runtime replay cases for hard scattered parent output, hard scattered final output, advisory integration improvement, and model-miss triage.
- [x] 6.3 Ensure fake-AI replay distinguishes PM decision support from `current_gate_blocker`.
- [x] 6.4 Add or update planning-quality tests for every new FlowGuard hazard and every nonblocking advisory countercase.

## 7. Focused Validation

- [x] 7.1 Run FlowGuard import, version, and project audit checks.
- [x] 7.2 Run focused planning-quality tests.
- [x] 7.3 Run card instruction coverage tests.
- [x] 7.4 Run integration Cartesian tests.
- [x] 7.5 Run current-contract Cartesian tests.
- [x] 7.6 Run fake-AI runtime replay tests.
- [x] 7.7 Run planning-quality, ContractExhaustionMesh, acceptance TestMesh, Model-Test Alignment, and model maturation runners.
- [x] 7.8 Fix any focused validation failure and rerun affected checks.

## 8. Broad Regression, Install Sync, And Topology

- [x] 8.1 Start or run meta model regression and preserve background artifacts under `tmp/flowguard_background/run_meta_checks.*`.
- [x] 8.2 Start or run capability model regression and preserve background artifacts under `tmp/flowguard_background/run_capability_checks.*`.
- [x] 8.3 Inspect background stdout, stderr, combined, exit, and meta artifacts before citing the regressions as complete.
- [x] 8.4 Rebuild FlowGuard project topology.
- [x] 8.5 Check FlowGuard project topology.
- [x] 8.6 Sync repository-owned FlowPilot install material.
- [x] 8.7 Audit local installed FlowPilot freshness.
- [x] 8.8 Run installed FlowPilot check and install self-check.
- [x] 8.9 Update FlowGuard adoption record if required by project audit/version drift.

## 9. OpenSpec, Git, And Closure

- [x] 9.1 Mark each completed task only after its implementation and validation evidence exist.
- [x] 9.2 Run OpenSpec status/apply verification for this change and keep artifacts current.
- [x] 9.3 Inspect git status and preserve unrelated peer-agent changes.
- [x] 9.4 Commit the scoped implementation and OpenSpec artifacts on the local branch after validation passes.
- [x] 9.5 Record a predictive-KB postflight observation if this work exposes a reusable process lesson or route gap.
- [x] 9.6 Complete the active goal only after current evidence proves every requested requirement, validation, install sync, topology, and git sync item is complete.
