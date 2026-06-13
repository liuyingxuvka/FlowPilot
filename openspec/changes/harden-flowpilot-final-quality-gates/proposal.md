## Why

FlowPilot already has the right final-quality flow, but the runtime must make
the existing gates mechanically strict: final evidence cannot count merely
because a review, FlowGuard, or validation id exists. This closes the remaining
gap between prompt/card requirements and automatic high-quality completion.

## What Changes

- Require final route-wide ledgers and final requirement evidence matrices to
  count only current-route evidence whose underlying record is passing,
  current, and unblocked.
- Treat blocked Reviewer decisions, failed or stale FlowGuard reports, failed
  validation evidence, and historical route evidence as unresolved final-gate
  material rather than closure proof.
- Require terminal backward replay results to cover the runtime-issued segment
  targets and to reject missing, duplicate, or unexpected segment ids.
- Keep the existing FlowPilot process, packet/result records, gate ledgers, and
  closure route. No fallback compatibility path, old-route migration path, or
  alternate quality workflow is introduced.
- Add focused negative tests and FlowGuard/model-test evidence so weak final
  proof cannot regress into a green completion claim.

## Capabilities

### New Capabilities

- `flowpilot-final-quality-gates`: Final FlowPilot closure gates only accept
  current, passing, unblocked evidence from the existing Reviewer, FlowGuard,
  validation, final-ledger, requirement-matrix, and terminal-replay surfaces.

### Modified Capabilities

- `flowpilot-closure-kernel`: Closure remains evidence-aware and must consume
  final quality-gate blockers rather than classifying closed-looking records as
  successful evidence.
- `formal-gate-review-standards`: Reviewer evidence is only final-gate evidence
  when the review is accepted, independent, current, and unblocked.
- `hard-gate-coverage-matrix`: Hard-gate coverage must include negative proof
  for blocked review, stale FlowGuard, failed validation, and incomplete
  terminal replay cases.

## Impact

- Runtime final gate helpers in
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Prompt cards that describe final ledger, closure, and terminal replay gate
  expectations, if wording must be clarified.
- Focused router/runtime tests under `tests/` and FlowGuard model-test
  alignment artifacts under `simulations/`.
- FlowGuard project adoption records, topology artifacts, install sync/audit,
  and local git state after validation.
