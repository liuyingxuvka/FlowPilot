## Why

FlowPilot can currently record stale or duplicate role submissions as blocked
results after a packet has already been accepted or superseded. That preserves
bad state in `result_ids`, lets later readers accidentally treat the newest
historical result as authority, and can encourage background agents to keep
retrying old packets.

## What Changes

- **BREAKING**: Reject stale, noncurrent, already-accepted, or inactive-lease
  result submissions at the `submit-result` ingress before allocating a
  `result_id`, writing `ledger["results"]`, or appending `packet["result_ids"]`.
- Keep a single current-contract path: only the current waiting packet with the
  current active assigned lease may submit a result.
- Make repeated `dispatch-current-role` calls idempotent for an already active
  current packet lease; replacement remains limited to the existing modeled
  repair/reissue path.
- Treat `accepted_result_id` as the sole authority for accepted packets. Keep
  `result_ids` as history, not as accepted-result authority.
- Harden projection and materialization so projection failures do not cause
  business-result resubmission or fallback acceptance of stale outputs.
- Clarify Reviewer hardening boundaries: runtime enforces mechanical fields,
  current-object binding, accepted-result binding, authorized-read/open
  receipts, and evidence existence; runtime does not perform semantic text
  grading or keyword matching.
- Strengthen every Reviewer review packet prompt/card so Reviewer is expected
  to actively inspect the work, open evidence, run relevant tests or FlowGuard
  checks, compare against models/contracts, and add or repair review-scope tests
  when that is the responsible way to prove or challenge quality.
- Extend FlowGuard, fake-AI, D-card, lifecycle, and model-test-alignment
  coverage for stale submit, duplicate submit, repeated dispatch, stale result
  authority, projection failure, and mechanically invalid Reviewer pass cases.
- Synchronize repository-owned install artifacts and the local installed
  FlowPilot skill after validation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-control-plane-contract-kernel`: stale, noncurrent, duplicate, and
  already-accepted packet result submissions become ingress rejections, not
  blocked result rows.
- `flowpilot-packet-review-flow`: accepted packet review and PM/Reviewer target
  selection use `accepted_result_id` rather than latest historical result.
- `runtime-ledger-persistence`: projection/materialization writes remain
  atomic and projection failure does not replay business submission.
- `formal-gate-review-standards`: Reviewer runtime gates stay mechanical and
  current-object-bound; Reviewer prompts/cards explicitly require active
  inspection, test/model execution, evidence checking, and review-scope test
  additions when appropriate; semantic review quality remains a
  Reviewer/FlowGuard and fake-AI coverage obligation, not runtime text
  matching.
- `synthetic-agent-coverage-matrix`: D-card and coverage rows include stale
  submit, duplicate submit, repeated dispatch, and Reviewer mechanical-gate
  bad cases.
- `multiround-fake-ai-control-rehearsal`: fake AI replay includes stale
  backend submissions and shallow Reviewer attempts that fail through
  mechanical evidence/currentness gates.

## Impact

- Runtime paths: `flowpilot_new.py`, new run commands, role dispatch commands,
  core runtime packet/result/lease submission, status projection, validation,
  and materialization helpers.
- FlowGuard models and runners in `simulations/`, especially packet/control
  plane and model-test alignment coverage.
- Tests covering lifecycle guard, fake-AI runtime replay, synthetic coverage
  matrix, Reviewer active challenge boundaries, and install/self-check sync.
- Local install synchronization through existing repository install/audit
  scripts. No UI surface, compatibility shim, legacy alias, fallback parser, or
  new parallel ledger is introduced.
