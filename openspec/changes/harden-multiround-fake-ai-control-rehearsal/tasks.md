## 1. Grounding

- [x] 1.1 Verify FlowGuard import, OpenSpec change status, and clean peer-agent workspace before implementation.
- [x] 1.2 Inventory current E2E synthetic chaos, real-Router dry-run, repair transaction, fast-tier, and model-test alignment evidence.

## 2. Matrix and Replay Evidence

- [x] 2.1 Add a multi-round no-producer PM repair row to the E2E synthetic chaos matrix.
- [x] 2.2 Add a real-Router rehearsal row for producer-proof repair recovery and stale-evidence rejection.
- [x] 2.3 Add known-bad matrix cases for no-producer repair waits and stale evidence used as fresh repair proof.
- [x] 2.4 Extend runtime replay tests so bad PM repair is rejected, corrected repair restores a legal wait, and producer evidence is visible.

## 3. Model-Test Alignment and Fast Gate

- [x] 3.1 Attach the new multi-round evidence ids to model-test alignment obligations.
- [x] 3.2 Update fast-tier assertions so the new matrices and tests cannot be silently dropped.
- [x] 3.3 Refresh generated JSON reports for updated matrices and model-test alignment.

## 4. Validation

- [x] 4.1 Run focused matrix and replay tests.
- [x] 4.2 Run FlowGuard repair transaction checks and model-test alignment checks.
- [x] 4.3 Run the fast tier and relevant real-Router rehearsal tests.
- [x] 4.4 Run Meta and Capability regressions in background and inspect final artifacts.

## 5. Sync and Finalization

- [x] 5.1 Validate the OpenSpec change.
- [x] 5.2 Synchronize repository-owned local FlowPilot installation and verify install freshness.
- [x] 5.3 Run predictive-KB postflight and record any reusable lesson.
- [x] 5.4 Commit the scoped local git change without pushing, publishing, tagging, or archiving.
