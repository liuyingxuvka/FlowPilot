## 1. Preflight And Scope

- [x] 1.1 Run predictive KB preflight, FlowGuard package/version audit, project audit, topology orientation, and existing OpenSpec review.
- [x] 1.2 Identify peer-agent modified files and keep edits scoped to the stage/evidence matrix upgrade.
- [x] 1.3 Validate this OpenSpec change before implementation closure.

## 2. Runtime Stage/Evidence Matrix

- [x] 2.1 Add the canonical stage/evidence matrix module and expose strict lookup helpers.
- [x] 2.2 Bind every current packet-result family to a matrix row; unknown current families must be validation failures, not generic fallback.
- [x] 2.3 Inject the subject matrix row into FlowGuard packets and review packets where stage semantics affect evidence timing.
- [x] 2.4 Update the high-standard contract packet wording so acceptance item evidence is future closure policy, not immediate product evidence.

## 3. Portable Installed Runtime Self-Check

- [x] 3.1 Add an installed-skill FlowPilot runtime self-check script that emits a JSON receipt from the installed skill root.
- [x] 3.2 Record a run-scoped self-check receipt at FlowPilot startup without requiring target projects to contain dev-repo `simulations/`.
- [x] 3.3 Update install checks and sync audits to require the new self-check script and matrix module in installed FlowPilot.
- [x] 3.4 Remove the hardcoded dev-repo model-test script from FlowGuard minimal report examples.

## 4. Prompt And Card Guidance

- [x] 4.1 Update FlowGuard operator cards to obey `subject_stage` and `subject_evidence_kind`.
- [x] 4.2 Update PM/FlowGuard loop cards so preplanning and plan packages project future evidence without claiming it exists.
- [x] 4.3 Keep terminal backward replay and final closure cards strict about direct current evidence.

## 5. FlowGuard Models And Coverage

- [x] 5.1 Add matrix fields and self-check receipt fields to FieldLifecycleMesh.
- [x] 5.2 Add information-flow rows for valid preplanning contract evidence, invalid premature terminal-evidence blocking, and invalid target-workspace dev-script requirement.
- [x] 5.3 Add model-test alignment obligations and ordinary test bindings for every matrix-owned stage class.
- [x] 5.4 Add ContractExhaustionMesh and Cartesian coverage for missing stage fields, wrong stage fields, premature blockers, fake package success, and dev-script target-project requirements.

## 6. Unit, Fake-AI, And Rehearsal Tests

- [x] 6.1 Add focused high-standard control-flow tests for first-package pass semantics and future-evidence non-requirement.
- [x] 6.2 Add negative tests proving result-stage and terminal-stage direct evidence gates are still strict.
- [x] 6.3 Add fake-AI and real-router dry-run coverage for all matrix package classes.
- [x] 6.4 Add install/entrypoint tests proving the installed runtime self-check receipt exists and is portable.

## 7. Validation, Sync, And Closure

- [x] 7.1 Run focused unit tests and model checks for changed runtime, prompt, field, alignment, exhaustion, and install surfaces.
- [x] 7.2 Run heavyweight Meta and Capability checks through the background artifact contract and inspect completion artifacts before claiming them.
- [x] 7.3 Rebuild and check FlowGuard project topology after model/test/runtime changes.
- [x] 7.4 Sync repository-owned FlowPilot install artifacts to the local installed skill and run install audits.
- [x] 7.5 Inspect final git status/diff without reverting peer-agent changes; commit only this change set if it can be staged safely.
- [x] 7.6 Perform predictive KB postflight and record a structured observation if this work exposes a reusable route gap.

## 8. Full Current-Contract Cartesian Coverage

- [x] 8.1 Add an import-safe generated Cartesian matrix for the bounded current-contract product across flow stage, packet/material family, action, object state, AI return profile, timing, blocker/repair state, route shape, execution source, and final-claim pressure.
- [x] 8.2 Add an executable matrix runner that streams the full materialized product, records reaction and owner coverage, audits reused existing tests, and fails any current-contract GlassBreak reaction.
- [x] 8.3 Add unit tests for axis coverage, no-GlassBreak reactions, absorbing next actions, old/stale/future/progress rejection, and existing-test currentness audits.
- [x] 8.4 Wire the current-contract Cartesian matrix into the synthetic coverage and full-model coverage inventory surfaces without treating synthetic rows as live AI proof.
- [x] 8.5 Run focused validations and refresh result artifacts for the new matrix, overlap audit, coverage sweep, and topology.
