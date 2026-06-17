## Why

FlowPilot terminal backward replay can currently reject a correct blocking
Reviewer result as a mechanical contract failure because the runtime contract
requires top-level `passed=true` before the semantic blocker path can run. This
turns a valid final-quality finding into repeated control-plane reissue work and
can hide the real repair instruction from PM.

## What Changes

- Allow terminal backward replay results to be mechanically valid in two
  current branches: a passing closure branch and a blocking repair branch.
- Keep closure strict: only the passing branch can record accepted terminal
  replay evidence or unlock final closure.
- Route the blocking branch through the existing terminal semantic blocker
  path so PM receives the actual blocker, failing segments, and restart policy.
- Preserve runtime-issued `segment_targets` on terminal replay reissue packets
  so a mechanical correction packet remains satisfiable.
- Add focused regression tests, fake-run coverage, and FlowGuard/model-test
  alignment rows for the negative terminal replay branch.
- Keep the current protocol only. No fallback parser, old result shape,
  historical promotion path, or alternate closure lane is introduced.

## Capabilities

### New Capabilities

- `terminal-ledger`: Terminal replay records distinguish passing closure
  evidence from blocking repair evidence and keep closure authority gated on
  the passing branch only.

### Modified Capabilities

- `flowpilot-control-plane-contract-kernel`: Terminal replay packet-result
  validation accepts current positive and negative review outcomes instead of
  requiring `passed=true` for every mechanically valid result.
- `hard-gate-coverage-matrix`: Hard-gate evidence must include the historical
  negative case where a valid terminal replay blocker previously became a
  mechanical reissue loop.

## Impact

- Runtime contract validation and packet reissue logic in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Terminal packet result catalog in
  `skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`
  and contract index/card wording if needed.
- Focused runtime/fake-run tests under `tests/`.
- FlowGuard model-test alignment and related result artifacts under
  `simulations/`.
- Repository install sync, installed-skill audit, and FlowGuard adoption logs
  after source validation.
