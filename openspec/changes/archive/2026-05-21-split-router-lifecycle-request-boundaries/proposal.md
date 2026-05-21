## Why

`flowpilot_router_lifecycle_requests.py` is still an oversized behavior owner
after the export-manifest contraction. It mixes terminal lifecycle request
writing, controller-work fencing, terminal authority reconciliation, protocol
dead-end persistence, terminal next-action construction, and exception blocker
fallbacks in one file.

This change reduces that structure debt now because the maintenance map already
flags the module as over the StructureMesh threshold, while the existing router
facade model has clear lifecycle-request ownership boundaries that can be split
without changing runtime behavior.

## What Changes

- Split lifecycle request internals into owner child modules under the existing
  `lifecycle_requests` boundary.
- Keep `flowpilot_router_lifecycle_requests.py` as the compatibility facade and
  keep the existing `flowpilot_router` private export names intact.
- Preserve lifecycle artifact schemas, run-state status transitions, terminal
  fences, terminal reconciliation receipts, protocol dead-end records, and
  exception-to-control-blocker behavior.
- Update FlowGuard StructureMesh/model-test evidence and maintainer maps for
  the new child-module topology.
- Run focused lifecycle/terminal/control-blocker tests and background router,
  Meta, and Capability regressions before claiming completion.

## Capabilities

### New Capabilities

- `router-lifecycle-request-boundaries`: Covers behavior-preserving lifecycle
  request owner splitting, retained compatibility facades, and FlowGuard-backed
  parity evidence for the terminal lifecycle request surface.

### Modified Capabilities

- `repository-maintenance-guardrails`: Adds lifecycle-request split completion
  expectations for local install sync, local git capture, and complete
  background evidence.

## Impact

- Affected source:
  `skills/flowpilot/assets/flowpilot_router_lifecycle_requests.py` and new
  lifecycle-request child owner modules.
- Affected evidence:
  router facade split catalog/targets, structure-maintenance catalog,
  model-test alignment contracts/results, maintenance maps, and install checks.
- Public/runtime behavior:
  no change to CLI behavior, router facade exports, lifecycle JSON schemas,
  event names, or terminal run semantics.
