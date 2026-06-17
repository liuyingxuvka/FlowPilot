# Consume FlowGuard Cartesian Shards And Receipts

## Why

FlowGuard 0.51 adds native Cartesian combination cases, coverage shards, and
model coverage receipts. FlowPilot already has a project-local Cartesian matrix,
but the matrix can still overclaim if it remains a hand-written coverage layer
that is not consumed through FlowGuard's canonical shard and receipt surfaces.

The most important miss is exact boundary drift: when an upstream contract or
historical failure emits a new mutation kind, FlowPilot must fail until that
mutation is declared in the Cartesian alphabet. It must not map the unknown
mutation to an older generic field error.

## What Changes

- Upgrade the FlowPilot Cartesian control-plane model to build a FlowGuard
  native `ContractExhaustionPlan` with axes, an interaction group, generated
  combination cases, model-owned coverage shards, and a coverage receipt.
- Attach combination case ids, coverage shard ids, and coverage receipt ids to
  applicable Cartesian cells.
- Require bridge rows to preserve source mutation kinds exactly; unknown source
  mutations become missing-family findings instead of fallback mappings.
- Route generated shard ids through the runner's TestMesh review so child
  suites own every required shard.
- Propagate shard/receipt identifiers into synthetic-agent coverage rows and
  tests.

## Non-Goals

- Do not add runtime compatibility aliases, fallback parsing, or old-field
  translation.
- Do not treat the new receipt as release confidence by itself.
- Do not broaden this pass into unrelated FlowPilot runtime repairs unless the
  upgraded matrix exposes a failing current-contract bug.

## Validation

- Validate this OpenSpec change.
- Run the upgraded Cartesian runner and pytest coverage.
- Run synthetic-agent coverage, model-test alignment, layered proof, inventory,
  test-tier, install, and topology checks affected by the new evidence chain.
