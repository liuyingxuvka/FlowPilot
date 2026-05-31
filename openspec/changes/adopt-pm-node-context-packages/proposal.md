## Why

FlowPilot now has the right node gate order, but FlowGuard and Reviewer packets
still depend too much on each role rediscovering the node context. PM should
author the minimum node context package once, and runtime should attach it to
FlowGuard, worker, and Reviewer packets without making it the review boundary.

## What Changes

- **BREAKING** Require each accepted node acceptance plan to include a PM-authored
  node context package.
- Attach the node context package to pre-work FlowGuard, worker, post-result
  FlowGuard, and Reviewer packets for the same node.
- Require runtime to reject or withhold downstream packets when the node context
  package is missing, stale for the current repair generation, or lacks required
  references.
- Require FlowGuard operators and Reviewers to treat the context package as the
  minimum starting point, not a scope limit.
- Preserve prompt isolation: the package carries references, criteria, risks,
  and inspection targets; it does not make all sealed bodies globally readable.

## Capabilities

### New Capabilities

- `pm-node-context-package`: PM-authored node context package attached to every
  formal node gate and downstream packet.

### Modified Capabilities

- `flowpilot-prework-flowguard-node-gate`: Pre-work FlowGuard packets must
  consume the current PM node context package.
- `flowpilot-packet-review-flow`: Reviewer packets must include the current PM
  node context package as starting evidence while preserving independent review.

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- Affected prompt cards: PM, FlowGuard operator, and Reviewer role cards.
- Affected FlowGuard model/checks: node pre-work gate model and model-test
  alignment source obligations.
- Affected tests: core runtime, high-standard control flow, recursive route
  execution, and install/card coverage checks.
