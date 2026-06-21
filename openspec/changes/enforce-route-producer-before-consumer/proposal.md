## Why

Recent FlowPilot route work exposed a planning-quality miss: a route can be
mechanically traversable while an early node's artifact still depends on output
from later unfinished nodes. This weakens the FlowGuard operator route-process
gate because coverage and serial traversal are not enough unless producer work
precedes consumer work.

## What Changes

- Require FlowPilot route planning and route-process review to check
  producer-before-consumer ordering for node artifacts, acceptance criteria,
  deliverable checks, and validation checks.
- Teach PM, FlowGuard operator, and Reviewer cards to use existing route fields
  and existing gate/blocker results to catch future-node dependencies.
- Keep fixes current-contract and minimal: no new schema fields, no
  compatibility path, no parallel dependency ledger, and no special README-only
  mechanism.
- Add focused regression coverage for inverted artifact dependencies and for a
  correctly ordered producer-before-consumer route.

## Capabilities

### New Capabilities

- `route-producer-consumer-ordering`: route viability includes checking that a
  node only consumes artifacts or evidence produced by earlier nodes, the
  current node, or already-available materials.

### Modified Capabilities

- None.

## Impact

- Affected prompt cards: PM route skeleton, FlowGuard operator route process
  check, Reviewer route challenge, PM node acceptance plan, and Reviewer node
  acceptance plan review.
- Affected tests/models: card instruction coverage and focused route/process
  ordering regression coverage.
- Affected validation: targeted unit/model checks, FlowGuard meta/capability
  checks when prompt/process model surfaces change, topology rebuild/check, and
  local install sync/audit.
