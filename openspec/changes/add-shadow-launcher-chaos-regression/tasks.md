## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, clean/owned repository state, and peer-agent boundaries.
- [x] 1.2 Create OpenSpec proposal, design, specs, and task checklist.
- [x] 1.3 Inventory existing launcher, CLI, daemon, background artifact, synthetic replay, real-Router rehearsal, TestMesh, and Model-Test Alignment surfaces.

## 2. Matrix

- [x] 2.1 Add a shadow launcher chaos regression matrix script and generated result JSON.
- [x] 2.2 Add matrix rows for installed launcher shadow flow, crash recovery, peer-agent conflict, upgrade migration, malformed package generator, and bounded soak loop.
- [x] 2.3 Add known-bad matrix cases for progress-only background evidence, stale peer proof, missing installed launcher evidence, direct state mutation, unbounded soak claims, and live-AI semantic overclaim.
- [x] 2.4 Add matrix tests for completeness, standard states, confidence boundaries, bad-case rejection, and finite package classes.

## 3. Runtime Regressions

- [x] 3.1 Add installed launcher shadow-flow test using the local installed FlowPilot skill plus real Router/CLI startup evidence.
- [x] 3.2 Add crash recovery test for stale locks, daemon death, duplicate resume, and progress-only proof rejection.
- [x] 3.3 Add peer-agent conflict test for shared artifact overwrite, stale proof reuse, and model evidence owner collision.
- [x] 3.4 Add upgrade migration test from older persisted state/install freshness to current standard state.
- [x] 3.5 Add malformed package generator tests for finite bad fake AI package classes.
- [x] 3.6 Add bounded soak-loop test that repeats startup/recovery/rejection/terminal cleanup and checks residue.

## 4. FlowGuard/TestMesh Alignment

- [x] 4.1 Register matrix and runtime tests in the fast tier.
- [x] 4.2 Register shadow launcher chaos obligations and evidence in FlowGuard Model-Test Alignment.
- [x] 4.3 Update tier/alignment tests so future changes cannot silently drop the new evidence.
- [x] 4.4 Record FlowGuard adoption evidence with commands, artifacts, scoped confidence, and skipped limits.

## 5. Validation

- [x] 5.1 Run focused matrix generation and matrix tests.
- [x] 5.2 Run focused runtime regression tests.
- [x] 5.3 Run synthetic coverage matrix, model-test alignment, and tier registration tests.
- [x] 5.4 Run fast tier, Meta, and Capability checks in background with final artifact inspection.
- [x] 5.5 Validate the OpenSpec change strictly.

## 6. Sync and Finalization

- [x] 6.1 Synchronize repository-owned local FlowPilot skill/install surface.
- [x] 6.2 Run install sync audit, install check, and local repository checks.
- [x] 6.3 Perform predictive-KB postflight and record a structured observation if this work exposes a reusable lesson.
- [x] 6.4 Commit local git state without pushing, publishing, tagging, deploying, or archiving.
