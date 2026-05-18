## Why

FlowPilot currently records run-local protocol observations and final reports, but a new formal run is not indexed in the shared Spark-style skill maintenance log. This makes it harder to find later what a FlowPilot-run task did and where its run folder lives.

## What Changes

- Add a lightweight PM bookkeeping step during material understanding.
- PM must find an existing shared Spark-style skill maintenance log, or create the same shared log format when none exists.
- PM appends one concise FlowPilot run row with the work summary, `skill: flowpilot`, workspace root, `run_id`, and run folder.
- PM reports the maintenance entry path/id in `pm_material_understanding.json` so Router can preserve the work report.
- Keep this non-gating: no reviewer approval, FlowGuard gate, route node, or project acceptance condition is introduced for the bookkeeping row.

## Capabilities

### New Capabilities

- `shared-skill-maintenance-log`: PM-owned lightweight indexing of each formal FlowPilot run in a shared Spark-style skill maintenance log.

### Modified Capabilities

- None.

## Impact

- PM material-understanding prompt card and PM core card.
- PM material-understanding template and runtime writer.
- Protocol/template documentation.
- Focused router material-understanding test coverage.
