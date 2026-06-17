# Harden FlowPilot Cartesian Control-Plane Exhaustion

## Why

FlowPilot already has contract-exhaustion checks for known packet/result
contracts, historical failures, and synthetic agent rows. The remaining miss is
not one missing field by itself; it is the absence of a declared finite product
over control-plane boundaries, mutation kinds, handoff contexts, consumers, and
recovery expectations.

That gap lets individual tests pass while a live route still fails when one
upstream artifact shape, missing body, stale path, wrong owner, or repeat
blocker is consumed by a different downstream control-plane actor than the test
covered. The fix must stay current-contract only: reject unsupported shapes,
emit precise repair instructions, and avoid compatibility aliases or fallback
guessing.

## What Changes

- Add a FlowGuard-backed Cartesian exhaustion model for FlowPilot control-plane
  materials.
- Declare the finite boundary inventory, mutation alphabet, state/handoff
  contexts, downstream consumers, and expected recovery reactions.
- Generate every product cell, including explicitly skipped impossible cells
  with a reason.
- Require each applicable cell to name the current subject, owner, repair
  command, evidence owner, expected reaction, and whether GlassBreak is allowed.
- Require normal repair drills to avoid GlassBreak; GlassBreak is only valid for
  explicit threshold probes that repeat the same blocker enough times.
- Connect the new matrix to TestMesh, Model-Test Alignment, synthetic-agent
  coverage, layered boundary proof, fast test tiers, and topology inventory.
- Add runtime/synthetic/historical regression tests that fail if a generated
  cell is unowned, unconsumed, lacks repair guidance, accepts fallback shapes, or
  routes normal repair through GlassBreak.

## Capabilities

- `flowpilot-cartesian-control-plane-exhaustion`

## Non-Goals

- Do not add legacy packet/result compatibility.
- Do not add fallback parsing, alias translation, old-router recovery, or
  prose guessing.
- Do not treat GlassBreak as a successful normal repair path.
- Do not replace the existing contract-exhaustion mesh; this change consumes and
  strengthens it.

## Validation

- Run the new Cartesian runner and write its result artifact.
- Run the new pytest module plus contract-exhaustion, synthetic-agent coverage,
  model-test alignment, layered boundary proof, coverage inventory, and test-tier
  tests.
- Rebuild/check the FlowGuard topology when model/runner/test registrations are
  updated.
- Run OpenSpec validation for this change.
