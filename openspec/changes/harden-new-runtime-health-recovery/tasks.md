## 1. Regression Grounding

- [x] 1.1 Add focused tests for accepted packets with stale active leases after reassignment.
- [x] 1.2 Add focused tests for body-free controller/status projection.
- [x] 1.3 Add focused tests for actionable `recover_or_reissue` payloads.
- [x] 1.4 Add focused tests proving nested node context packages are rejected.
- [x] 1.5 Add focused tests for stable evidence summary finalization.
- [x] 1.6 Add focused tests for terminal current pointer status.

## 2. Runtime Fixes

- [x] 2.1 Supersede older active packet leases on reassignment.
- [x] 2.2 Add accepted-packet active-lease health findings to final preflight.
- [x] 2.3 Add redacted/body-free ledger projection helpers for controller surfaces.
- [x] 2.4 Extend foreground recovery duty with concrete command payloads.
- [x] 2.5 Reject nested `node_acceptance_plan.node_context_package`; only top-level `node_context_package` is accepted.
- [x] 2.6 Add stable evidence summary manifest finalizer.
- [x] 2.7 Update current pointer refresh to show terminal status after terminal return.
- [x] 2.8 Add compact default status output and explicit full/debug mode.

## 3. FlowGuard and Model/Test Alignment

- [x] 3.1 Update the focused core-runtime FlowGuard runner with the new stale-lease and projection scenarios.
- [x] 3.2 Update known-friction or model-test alignment evidence for the `run-20260531-210441` friction family.
- [x] 3.3 Rebuild/check project topology when model/test surfaces change.

## 4. Sync and Verification

- [x] 4.1 Run focused unit tests for the changed runtime surfaces.
- [x] 4.2 Run focused FlowGuard checks.
- [x] 4.3 Start heavyweight model regressions in the documented background log contract and inspect completion artifacts.
- [x] 4.4 Run install sync, install check, local install audit, and smoke checks.
- [x] 4.5 Verify git diff is scoped and does not revert unrelated peer-agent work.
