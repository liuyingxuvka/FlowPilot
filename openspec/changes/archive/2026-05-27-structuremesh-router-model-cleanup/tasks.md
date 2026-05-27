## 1. Baseline And Guardrails

- [x] 1.1 Preserve a rollback backup with HEAD, status, working-tree diff, and staged diff.
- [x] 1.2 Verify real FlowGuard import and schema version before modeling.
- [x] 1.3 Validate this OpenSpec change strictly before production-code edits.
- [x] 1.4 Record the starting structure inventory and remaining hotspots.

## 2. FlowGuard Maintenance Gates

- [x] 2.1 Add an executable StructureMesh model/check for the router split.
- [x] 2.2 Add known-bad StructureMesh hazards for missing owner, duplicate root state owner, missing facade, removed entrypoint, stale parity, and insufficient release evidence.
- [x] 2.3 Add an executable TestMesh model/check for router runtime child suites and background artifact completeness.
- [x] 2.4 Add StructureMesh evidence for the completed model-script facade splits so remaining model split obligations are visible.
- [x] 2.5 Wire the new maintenance checks into install/public validation surfaces where appropriate.

## 3. Router Structure Split

- [x] 3.1 Re-evaluate external-event family helpers without moving root wait/idempotency persistence out of the facade.
  - Existing `flowpilot_router_event_intake.py` and `flowpilot_router_events.py` remain the safe split boundary; no additional body movement was forced.
- [x] 3.2 Re-evaluate daemon loop helpers while preserving daemon status and startup behavior.
  - Existing `flowpilot_router_startup_daemon.py` remains the safe split boundary.
- [x] 3.3 Re-evaluate bootloader/startup action helpers behind existing public functions.
  - Deferred beyond existing helper surfaces because the remaining action body still writes shared startup/root state.
- [x] 3.4 Re-evaluate PM role-work helpers behind existing action/event names.
  - Deferred because the remaining function still crosses PM packet creation, busy-state projection, and root wait ownership.
- [x] 3.5 Re-evaluate terminal ledger helpers behind existing terminal behavior.
  - Deferred because the remaining body owns final route-wide ledger writes and terminal state reconciliation.
- [x] 3.6 Re-evaluate control-blocker repair helpers where focused parity tests exist.
  - Deferred because the remaining body still shares repair transaction state with root blocker writes.
- [x] 3.7 Keep `flowpilot_router.py` as the compatibility facade and root state coordinator.

## 4. Model And Test Helper Split

- [x] 4.1 Split the persistent router daemon model into state, transitions, invariants, and hazards if focused parity evidence is stable.
- [x] 4.2 Split the prompt-isolation model into state, transitions, invariants, and hazards if focused parity evidence is stable.
- [x] 4.3 Split cross-plane friction audit/transition/hazard helpers if focused parity evidence is stable.
- [x] 4.4 Re-evaluate `tests/router_runtime/common.py`; defer this pass because model-script splits are lower-risk and already have focused parity runners.
- [x] 4.5 Defer any candidate whose StructureMesh, ModelMesh, or focused test evidence is not stable.

## 5. Documentation And Evidence

- [x] 5.1 Update structure baseline and verification matrix documents for the new gates and split boundaries.
- [x] 5.2 Update HANDOFF, README, CHANGELOG, and FlowGuard adoption log with the completed maintenance evidence.
- [x] 5.3 Keep generated or timestamp-only result changes out of the final diff unless they represent meaningful validation evidence.
- [x] 5.4 Add FlowGuard Model-Test Alignment documentation that maps major model obligations to ordinary tests and explicit gaps.
- [x] 5.5 Update FlowPilot PM, officer, and reviewer cards so model-backed approval reports cite model obligations, ordinary test evidence, missing test kinds, and conformance boundaries.

## 6. Model-Test Alignment And TestMesh Split

- [x] 6.1 Add an executable FlowGuard Model-Test Alignment runner using `ModelObligation`, `TestEvidence`, `ModelTestAlignmentPlan`, and `review_model_test_alignment()`.
- [x] 6.2 Add known-bad alignment cases for missing evidence, stale evidence, progress-only background evidence, orphan tests, duplicate same-kind evidence, and model-confidence overclaims.
- [x] 6.3 Split the broad router test-tier commands into smaller child suites for packet runtime, packets, cards, ACK/return, boundaries, route mutation, user-flow, terminal, closure, resume, control blockers, PM role work, quality gates, and material/modeling.
- [x] 6.4 Update TestMesh/structure maintenance evidence so the new child suites have one owner each and the parent router tier is composition-only.
- [x] 6.5 Add focused unit tests for the alignment runner and revised test-tier command plan.

## 7. Validation

- [x] 7.1 Run py_compile for all touched Python files.
- [x] 7.2 Run focused unit/model tests for each touched boundary.
- [x] 7.3 Run the Model-Test Alignment, StructureMesh/TestMesh, and model hierarchy checks and inspect their result artifacts.
- [x] 7.4 Run router runtime child suites with the background artifact contract where needed.
- [x] 7.5 Run layered Meta and Capability parent checks through background artifacts; do not run old legacy full checks.
- [x] 7.6 Run OpenSpec strict validation for this change and all active changes.
- [x] 7.7 Run install sync, install check, local install audit, public release boundary check, smoke check, and git whitespace checks.

## 8. Sync And Commit

- [x] 8.1 Synchronize the local installed FlowPilot skill from repo-owned source after final source edits.
- [x] 8.2 Confirm the working tree only contains intentional changes.
- [x] 8.3 Commit locally on `main` after validation.
- [x] 8.4 Confirm no extra branches were created and no push/release was performed.
- [x] 8.5 Run the KB postflight check and record any reusable lesson.
