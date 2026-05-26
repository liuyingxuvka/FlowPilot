## 1. Grounding And Model Miss Setup

- [x] 1.1 Verify real FlowGuard import, repository coordination state, and current OpenSpec evidence boundaries.
- [x] 1.2 Inventory existing repair, daemon, status, ACK, lifecycle, output-contract, historical replay, and background-observability tests.
- [x] 1.3 Add or update a known-friction regression matrix that records the six accepted friction surfaces, their historical bad cases, required models, tests, and scoped/full confidence rules.

## 2. FlowGuard Model And Alignment

- [x] 2.1 Extend repair transaction and control-plane friction FlowGuard coverage for PM decision flag atomicity and non-executable active blocker waits.
- [x] 2.2 Extend daemon/persistent-daemon coverage for repair finalization interleavings without skipped live projection claims.
- [x] 2.3 Extend model-test alignment so known-friction rows require concrete tests and cannot be satisfied by model-only or skipped evidence.
- [x] 2.4 Extend background-observability checks so progress-only, timed-out, skipped, or model-only evidence is classified as scoped or failing for known-friction gates.

## 3. Runtime Fixes

- [x] 3.1 Fix PM control-blocker repair finalization so active blocker waits, repair transactions, indexes, and daemon-visible flags are committed as one post-decision state.
- [x] 3.2 Fix material `packet_reissue` continuation so the next action relays or waits on the fresh producer instead of stale PM-decision wording.
- [x] 3.3 Harden worker material-scan result contract handling with realistic missing-self-check metadata fixtures and recoverable failure projection.
- [x] 3.4 Fix current status projection so committed PM decisions, resolved ACKs, active material generations, and stopped runs display from latest facts.
- [x] 3.5 Fix ACK projection so ACK-only receipt clearance cannot reappear as a missing-ACK blocker while semantic role work remains pending.
- [x] 3.6 Fix controlled stop reconciliation across current pointer, run lifecycle, daemon status, heartbeat/manual-resume, pending Controller actions, and role continuation state.

## 4. Historical Replay And Tests

- [x] 4.1 Add historical bad-case replay fixtures for Worker self-check failure, PM repair atomicity, packet reissue continuation, stale status, ACK false alarm, and controlled stop.
- [x] 4.2 Add focused runtime tests through real Router/role-output/status/lifecycle surfaces for all six friction rows.
- [x] 4.3 Add daemon/interleaving replay tests that compute daemon-visible next action immediately after PM repair decision commit.
- [x] 4.4 Add known-bad tests that prove missing fixtures, skipped live audit, model-only daemon checks, and progress-only background artifacts are rejected.
- [x] 4.5 Register new tests in the fast/router test tier and generated model-test alignment evidence.

## 5. Validation

- [x] 5.1 Run focused unit/runtime tests for repair transaction, material modeling, output contracts, ACK/status, daemon, lifecycle, and known-friction matrix.
- [x] 5.2 Run affected FlowGuard checks and update generated result JSON.
- [x] 5.3 Run router fast tier and inspect final foreground/background evidence.
- [x] 5.4 Run Meta and Capability model regressions in background using `tmp/flowguard_background/`, then inspect exit/meta/stdout/stderr/combined artifacts.
- [x] 5.5 Run strict OpenSpec validation for the change.

## 6. Sync And Finalization

- [x] 6.1 Synchronize repository-owned installed FlowPilot skill after source validation.
- [x] 6.2 Run install check and local install sync audit after synchronization.
- [x] 6.3 Perform predictive-KB postflight and record a structured observation for any reusable validation or route lesson.
- [x] 6.4 Review git diff, stage intended files only, and commit local git state without pushing, publishing, tagging, deploying, or archiving.
