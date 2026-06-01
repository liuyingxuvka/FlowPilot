## Context

The recursive route runtime was restored with a prose parser and a fallback to active route steps. That was acceptable for early rehearsal, but it is now the wrong authority boundary: PM route planning is a contract, not text to be guessed. A later PM result used structured JSON, the runtime failed to read it, fell back to the fixed bootstrap route, and final closure could pass without checking the user-visible deliverables.

## Goals / Non-Goals

**Goals:**

- Make PM route materialization schema-driven and exact.
- Preserve the user's requested no-fallback posture.
- Make route-declared deliverable checks system-owned terminal blockers.
- Keep current high-standard node acceptance, FlowGuard, review, validation, PM disposition, and parent replay gates intact.

**Non-Goals:**

- No compatibility shim for numbered text, `route_nodes`, or historical bootstrap steps.
- No PM-text route inference.
- No arbitrary shell-command deliverable execution during terminal closure.
- No OpenSpec archive, public release, or git commit in this implementation turn.

## Decisions

1. The only accepted PM route-plan body is JSON with `schema_version: "flowpilot.route_plan.v1"` and non-empty `nodes`.
   - Alternative considered: accept both `nodes` and `route_nodes`. Rejected because the requested target is a clean new-only FlowPilot contract.
2. Each node must provide `node_id` and `title`; defaults are not generated for missing identity.
   - Alternative considered: keep generated IDs. Rejected because schema shape, not parser guesswork, should define route cardinality and identity.
3. Deliverable checks are declared as data and evaluated by the runtime with bounded built-in check kinds.
   - Alternative considered: let Reviewer or FlowGuard reports claim deliverable acceptance. Rejected because terminal closure must independently check concrete deliverable artifacts.
4. Final closure consumes the rebuilt final route-wide ledger and final requirement evidence matrix.
   - Alternative considered: check deliverables only during node acceptance. Rejected because later route changes or missing final artifacts can stale node-local confidence.

## Risks / Trade-offs

- Existing tests or scripts that still emit numbered plans will fail. Mitigation: update them to emit the formal schema and add a negative regression for numbered text.
- Strict schema errors may surface earlier and feel less forgiving. Mitigation: produce explicit `BlackBoxRuntimeError` messages naming the missing schema or invalid field.
- Path checks cannot prove semantic quality. Mitigation: path checks are terminal blockers only; existing FlowGuard, review, validation, and PM disposition gates remain required.
