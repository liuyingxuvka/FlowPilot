## Why

FlowPilot now emits structured `review_window` metadata for Reviewer packets,
but the current evidence still proves representative review paths more strongly
than it proves every active review flow. A stronger gate is needed so every
runtime-issued Reviewer flow has declared material scope, authorized reads,
stage boundaries, and fake-AI Cartesian rehearsal evidence before broad
coverage is claimed.

## What Changes

- Add a review-window completeness matrix that enumerates every current
  Reviewer flow by stable `review_flow_id`, subject family, lifecycle stage,
  required window paths, required material classes, authorized-read
  obligations, forbidden future-stage demands, and PM repair/recheck return
  path.
- Extend the existing contract-exhaustion/current-contract coverage model with
  generated review-window completeness cells instead of creating a parallel
  reviewer framework.
- Extend the existing contract-driven fake AI responder with
  review-window-aware profiles for shallow pass, skipped required reads,
  future-stage demands, unauthorized sealed-body requests, invented scope,
  reviewer self-repair, PM bypass attempts, corrected retry, repeated no-delta
  failures, and break-glass threshold behavior.
- Add focused runtime tests proving review packets carry complete structured
  windows for each declared flow and reject or surface precise failures for
  missing, wrong, stale, mismatched, or prose-only window material.
- Add model/test alignment and test-tier evidence so the new matrix cannot be
  counted as full coverage unless every generated cell has a current owner.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `formal-gate-review-standards`: Reviewer packets must have complete
  runtime-checkable review windows for every active review flow, not only
  prose review scope or a representative packet.
- `synthetic-agent-coverage-matrix`: synthetic coverage must include
  review-window completeness cells and per-cell evidence ownership.
- `multiround-fake-ai-control-rehearsal`: fake AI rehearsals must include
  review-window-aware reviewer/PM behavior profiles and retry-threshold
  coverage.
- `flowpilot-control-plane-contract-kernel`: control-plane packet contracts
  must project review-window material scope and authorized-read obligations
  before Reviewer response.
- `tiered-flowpilot-test-validation`: validation tiers must include the new
  review-window completeness checks and keep release/background evidence
  boundaries visible.

## Impact

- Affected code: review-window generation/projection, contract-driven fake AI
  responder, contract-exhaustion/current-contract matrices, and focused
  runtime tests.
- Affected models/tests: review-window completeness model/cells, fake AI
  rehearsal checks, model-test alignment checks, high-standard control-flow
  tests, contract-exhaustion mesh checks, topology checks, and install checks.
- Affected prompts/cards: only minimal Reviewer/PM wording if existing cards do
  not already tell roles to obey the structured window and repair/recheck path.
