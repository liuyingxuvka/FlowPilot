## Why

Recent FlowPilot live-run inspection showed a gap between the intended
independent-checker rule and runtime behavior: a result producer can still be
assigned as the FlowGuard operator that checks that same result, and the parent
backward replay path can look like Reviewer -> FlowGuard -> Reviewer even
though the first Reviewer-produced replay is already the substantive parent
composition check.

This change tightens the existing current-contract path without adding fields,
legacy compatibility, fallback parsing, or a second review workflow.

## What Changes

- Reject checker self-review at both role assignment and result-submission
  validation for Reviewer review packets and FlowGuard post-result check
  packets.
- Preserve normal role reuse: a Reviewer or FlowGuard operator may be reused for
  later packets when the target result was produced by a different agent.
- For parent backward replay only, let a passing FlowGuard post-result check
  close the parent replay and release the existing PM disposition path instead
  of issuing a second Reviewer packet for the Reviewer-produced replay result.
- Keep blocker history append-only, but ensure current status, console, and
  gate decisions use only current-effective blockers or explicit PM decision
  gates.
- Add focused regression and model/check coverage for the observed live-run
  class and the non-regression cases.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-packet-review-flow`: checker independence and parent backward
  replay release ordering become explicit current-contract requirements.
- `blocker-repair-policy`: active blocker projections must exclude stale
  historical blocker rows that are no longer current-effective.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Runtime contracts and evidence wording where needed:
  `packet_result_contracts.py` and packet stage evidence metadata.
- Focused tests: core runtime, complete-system role reuse, parent backward
  route replay, blocker projection, and FlowGuard scenario/model checks.
- Validation: OpenSpec strict validation, focused pytest/unittest targets,
  FlowGuard model checks, topology refresh, install sync/audit/check.
