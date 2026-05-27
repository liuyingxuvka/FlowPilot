## Why

`flowpilot_router_protocol_external_event_data.py` is over the current
StructureMesh line threshold, but it is a canonical phase-indexed data table.
It has no functions, classes, state writes, or duplicated effect paths to
shorten. Splitting it again would optimize for line count instead of reducing
logic risk.

## What Changes

- Mark the external-event data table as an explicit StructureMesh skip in the
  full model-test-code diagnostic.
- Keep the existing external-event table contract evidence in place.
- Count this row separately from deferred split candidates so future heartbeat
  rounds do not keep trying to split a table-only surface.

## Impact

- No FlowPilot runtime behavior changes.
- The remaining StructureMesh backlog shrinks by one useful/safe decision.
- Future pruning rounds stay focused on real decision/effect paths rather than
  declarative data rows.
