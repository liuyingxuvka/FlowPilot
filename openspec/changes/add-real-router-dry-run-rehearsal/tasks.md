## 1. Grounding

- [x] 1.1 Verify real FlowGuard import, repository state, and coordination boundaries.
- [x] 1.2 Create OpenSpec change `add-real-router-dry-run-rehearsal`.
- [x] 1.3 Inventory existing Router CLI/runtime, E2E chaos, control-plane canary, TestMesh, and model-test alignment surfaces.

## 2. Rehearsal Matrix

- [x] 2.1 Add a real-Router dry-run rehearsal matrix script and generated result JSON.
- [x] 2.2 Add rows for full startup-to-terminal fake AI packages, public Router CLI boundary, compounded resume/proof recovery, and authority/overclaim rejection.
- [x] 2.3 Add known-bad matrix cases for missing ACK/receipt, invented events, direct state mutation, progress-only proof, non-terminal final state, and live-AI semantic overclaim.
- [x] 2.4 Add matrix tests for completeness, scoped confidence, evidence freshness, entrypoint coverage, and known-bad rejection.

## 3. Runtime Rehearsal

- [x] 3.1 Add a full-flow runtime rehearsal test using real Router, cards, packets, role-output envelopes, proof gates, and terminal lifecycle.
- [x] 3.2 Add a public Router CLI boundary test covering `start`, `state`, `next`, `apply`, `record-event`, and `run-until-wait`.
- [x] 3.3 Add a recovery/proof rehearsal test covering dead-daemon resume, duplicate resume idempotency, progress-only proof rejection, and final proof acceptance.
- [x] 3.4 Fix discovered runtime bugs without weakening hard invariants.

## 4. FlowGuard/TestMesh Alignment

- [x] 4.1 Register the new matrix and runtime tests in the fast tier.
- [x] 4.2 Update tier assertions so future changes cannot silently drop rehearsal evidence.
- [x] 4.3 Register real-Router dry-run rehearsal as FlowGuard Model-Test Alignment evidence with happy, edge, and negative/failure coverage.
- [x] 4.4 Record FlowGuard adoption evidence with commands, results, skipped steps, scoped confidence, and generated artifacts.

## 5. Validation

- [x] 5.1 Run focused matrix generation and matrix tests.
- [x] 5.2 Run focused runtime rehearsal tests.
- [x] 5.3 Run model-test alignment and fast-tier tests.
- [x] 5.4 Run affected router/model regressions in background and inspect final artifacts before claiming completion.
- [x] 5.5 Validate the OpenSpec change strictly.

## 6. Sync and Finalization

- [x] 6.1 Synchronize repository-owned local FlowPilot skill/install surface.
- [x] 6.2 Run install sync audit, install check, and local repository checks.
- [x] 6.3 Perform predictive-KB postflight and record a structured observation if this work exposes a reusable lesson.
- [x] 6.4 Commit local git state without pushing, publishing, tagging, deploying, or archiving.
