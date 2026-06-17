## 1. Preflight And OpenSpec

- [x] 1.1 Run predictive KB, FlowGuard package/version, project audit, topology, handoff, and coordination preflight.
- [x] 1.2 Upgrade the FlowGuard project record to installed FlowGuard when required and rerun project audit.
- [x] 1.3 Create proposal, design, and specs for route-authority singularity.

## 2. FlowGuard Model

- [x] 2.1 Add `simulations/flowpilot_route_authority_singularity_model.py` covering single owner, legal action visibility, wrong-path rejection, role-overreach, stale snapshots, old alias/fallback rejection, repeated no-delta, and corrected retry.
- [x] 2.2 Add `simulations/run_flowpilot_route_authority_singularity_checks.py` and generated result artifact.
- [x] 2.3 Extend ModelMesh with route-authority singularity hazards so parent mesh blocks when evidence is missing, stale, conflicted, or fallback-like.

## 3. Runtime And Registry

- [x] 3.1 Add route-authority snapshot fields or derivation helpers using the existing route action policy registry as the single source of truth.
- [x] 3.2 Add wrong-path rejection feedback for out-of-legal-set route/control submissions, including current owner, state family, legal actions, forbidden actions, and required repair command.
- [x] 3.3 Ensure unsupported old aliases, wrapper/prose shapes, and fallback-like route actions are rejected, not translated.
- [x] 3.4 Surface route-authority fields in PM/reviewer/FlowGuard/worker packet or card contexts only where they are current-contract guidance.

## 4. Tests And Synthetic Replay

- [x] 4.1 Add targeted router/runtime tests for owner conflict, no owner, PM wrong path, wrong role, old alias, fallback/prose rejection, and corrected retry.
- [x] 4.2 Extend synthetic agent coverage matrix with fake-AI wrong-path, no-delta repeat, role-overreach, and corrected retry rows.
- [x] 4.3 Extend synthetic agent trace replay tests for wrong-path rejection and repair-command-guided correction.

## 5. Alignment, Field Lifecycle, And Topology

- [x] 5.1 Add route-authority singularity family rows to model-test alignment and field lifecycle projection for behavior-bearing authority fields.
- [x] 5.2 Rebuild generated topology after model/test/runtime surfaces change.
- [x] 5.3 Record FlowGuard adoption evidence for the change.

## 6. Validation And Sync

- [x] 6.1 Run OpenSpec strict validation for this change.
- [x] 6.2 Run focused FlowGuard route-authority, legal-next-action, ModelMesh, model-test alignment, and synthetic coverage checks.
- [x] 6.3 Run targeted router/runtime and synthetic replay unit tests.
- [x] 6.4 Run broader project-control and skill/capability regressions in background where practical, then inspect final artifacts before using them as evidence.
- [x] 6.5 Sync repo-owned FlowPilot install, audit local install sync, run install check, and compile touched Python files.
- [x] 6.6 Run KB postflight, update tasks/evidence, and commit the local git version without reverting peer-agent work.
