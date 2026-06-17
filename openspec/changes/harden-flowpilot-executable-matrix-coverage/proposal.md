## Why

FlowPilot now has broad current-contract Cartesian coverage, but recent fake
project rehearsals exposed bugs that the model-only matrix did not catch:
packet body schema drift, public CLI worker lifecycle problems, repeated
reissue loops, terminal supplemental repair lineage gaps, stale result evidence,
and overclaims from old result artifacts. This change makes coverage claims
executable: high-risk model cells must be consumed by prepared fake AI packet
bodies, public Runtime/CLI replay, event-log liveness checks, and fresh result
receipts before they can support broad confidence.

## What Changes

- Add an executable coverage bridge that maps current-contract model cells to
  required fake AI bodies, runtime entrypoints, event-log evidence, convergence
  rules, and result-freshness receipts.
- Add executable matrix rows for the bug families surfaced by current fake
  project rehearsals: missing `current_evidence_refs`, old/moved/deleted stage
  fields, terminal `route_segment_replay` and `final_blockers`, terminal
  supplemental repair contracts, FlowGuard semantic recheck repair obligations,
  old alias rejection, wrong-role leases, missing ACK, stale node evidence,
  wrong FlowGuard target, dead leases, route mutation without frontier rewrite,
  slow reviewer progress, accepted packet reassignment, orphan runner summary,
  unsupported side commands, and public CLI worker lifetime.
- Separate normal recoverable-path expectations from break-glass safety
  expectations. Known recoverable paths must not enter break-glass, while the
  explicit fifth same-class no-progress repeat must enter Controller
  break-glass as a safety fuse.
- Upgrade existing synthetic/fake/rehearsal matrix reporting so rows are
  classified as model-only, fake-body, Runtime/CLI replay, long-chain
  convergence, or stale/weak evidence.
- Require stale result detection for coverage artifacts used by install,
  topology, model-test alignment, or final confidence claims.
- Preserve the current new-only runtime rule: old aliases, wrappers, fallback
  prose, newest-run fallback, repo-root fallback, and historical artifact
  promotion remain negative cases, not compatibility paths.

## Capabilities

### New Capabilities

- `flowpilot-executable-matrix-coverage`: Defines the bridge from model-local
  Cartesian cells to executable fake AI packet bodies, Runtime/CLI replay rows,
  event-log convergence checks, break-glass repeat thresholds, and freshness
  receipts.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: Synthetic coverage rows must distinguish
  model-only evidence from executable fake-body and Runtime/CLI replay evidence.
- `multiround-fake-ai-control-rehearsal`: Multi-round rehearsals must include
  bounded repeated-error convergence and fifth-repeat break-glass safety rows.
- `real-router-dry-run-rehearsal`: Real-Router rehearsal rows must bind public
  CLI entrypoints, worker lifecycle behavior, and current event-log receipts.
- `end-to-end-chaos-coverage-matrix`: Full-flow chaos rows must consume
  executable coverage bridge case ids and cannot rely on matrix-only proof.
- `end-to-end-synthetic-agent-chaos-replay`: Full-flow fake AI replay must
  prove the prepared packet body and public runtime path for accepted bridge
  rows.
- `tiered-flowpilot-test-validation`: Parent tiers must treat executable matrix
  child suites and freshness receipts as required child evidence for broad
  confidence.
- `controller-break-glass-repair`: Break-glass remains forbidden for known
  recoverable paths but required for the explicit fifth same-class no-progress
  repeat.

## Impact

- New FlowGuard model/checker and result artifact for executable matrix
  coverage under `simulations/`.
- New tests covering the bridge, fake packet body rows, public CLI replay
  receipts, long-chain convergence, break-glass threshold semantics, and stale
  result detection.
- Updates to coverage inventory/model-test alignment/TestMesh evidence so
  model-only green results cannot be cited as executable confidence.
- Possible focused updates to fake project rehearsal helpers where existing
  scenarios need to emit or consume bridge receipts.
- Local install sync and install checks must consume current result artifacts
  after model/test/runtime changes.
