## Why

Multiple FlowPilot control-plane defects have recurred after adjacent fixes and
green test reports because historical live failures were not promoted into hard
regression gates. This change turns the known six friction surfaces from
scoped fixes into replayable contracts that must pass through real Router,
daemon, packet, status, lifecycle, and install surfaces before confidence is
claimed.

## What Changes

- Add a known-friction regression gate that binds the six accepted friction
  surfaces to historical bad cases, model obligations, runtime replay tests,
  daemon interleaving checks, and user-visible status/lifecycle assertions.
- Harden PM control-blocker repair commits so post-decision state, active
  blocker allowed events, repair transaction records, and daemon-visible run
  state are observed atomically.
- Harden material repair continuation so a valid `packet_reissue` repair does
  not leave the user-visible control plane in a stale "waiting for PM" or
  non-executable blocker state.
- Harden worker material-scan result contracts with realistic role-output
  fixtures and failure recovery semantics, including the exact missing
  self-check metadata class observed in live runs.
- Harden ACK/status projection so receipts, completion, current action text,
  and blocker language cannot drift apart.
- Harden controlled stop so a user stop reconciles daemon, heartbeat/manual
  resume, current-run pointers, and role-agent continuation state as one
  lifecycle boundary.
- Add completion-evidence guardrails so skipped live audits, model-only checks,
  progress-only background logs, and daemon timeouts cannot be reported as full
  pass evidence.

## Capabilities

### New Capabilities

- `known-friction-regression-gates`: Defines the hard replay, modeling, and
  evidence contract for historical FlowPilot control-plane friction surfaces.

### Modified Capabilities

- `executable-repair-transactions`: Requires PM repair commits to expose only
  currently executable post-decision wait events and to resume material repair
  without stale pre-decision projection.
- `persistent-router-daemon`: Requires daemon/interleaving checks for repair
  transaction finalization and rejects transient half-committed blocker states.
- `controller-user-status`: Requires current status and user-facing summaries to
  derive from the latest reconciled run facts, not stale action or ACK text.
- `system-card-ack-clearance`: Requires ACK receipt status to stay separate
  from role-output completion and user-visible blocker wording.
- `daemon-lifecycle-recovery`: Requires controlled stop to reconcile daemon,
  heartbeat/manual-resume, current-run pointers, and role-agent continuation
  state.
- `flowguard-background-observability`: Requires final background artifacts and
  skipped-check disclosures before any model or live regression is counted as
  passed.

## Impact

- Router repair event handlers, active blocker wait validation, material repair
  continuation, pending action/status projection, ACK clearance, lifecycle stop
  handling, and background check evidence classification.
- FlowGuard models and checks for repair transactions, daemon reconciliation,
  persistent daemon, model-test alignment, slow/background evidence, and
  control-plane friction.
- Runtime tests under `tests/router_runtime/`, output-contract tests, status
  projection tests, lifecycle tests, and historical replay matrices.
- OpenSpec, FlowGuard adoption records, generated result JSON, local installed
  FlowPilot skill synchronization, install audit, and local git commit.
