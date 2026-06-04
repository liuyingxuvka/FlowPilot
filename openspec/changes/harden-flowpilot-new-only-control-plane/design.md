## Context

The previous current-target repair made stale packet references visible and
blocked several noncurrent routes. The remaining friction is narrower: old
same-family blockers can stay active after the newer repair path exists, result
parsing can still turn unsupported text into a pass, PM repair decisions still
have alias/fallback fields, and the formal entrypoint text still advertises an
old router diagnostic path.

## Decision

Use the current runtime records as the single authority:

- Packet/results stay append-only as history, but current routing ignores stale
  historical targets.
- A same-family blocker is defined by blocker class, subject/target packet,
  PM/repair lineage, gate/effect kind, and target role. When a newer record in
  that family becomes current, older active or awaiting-recheck blockers are
  retired with an explicit non-active status.
- Packet outcome parsing requires an explicit JSON object with the current
  `decision` field. Unknown or missing values produce a mechanical protocol
  block instead of passing silently.
- PM repair decision parsing accepts only the current top-level shape. Fallback
  fields are removed.
- Final preflight checks current active blockers and gates, then rejects any
  stale live reference that was not retired. Historical retired blockers do not
  block.
- Old compatibility entrypoints are removed from formal CLI/help/docs; test-only
  rehearsal helpers may remain internal if they are not advertised as runtime
  alternatives.

## FlowGuard Model

The existing `flowpilot_control_plane_friction` model owns this risk family.
Extend it instead of creating a parallel model:

- `old_blocker_active_after_new_repair`: must fail before the repair and pass
  when the old blocker is retired.
- `unknown_packet_outcome_defaults_pass`: must be impossible.
- `pm_decision_alias_or_nested_wrapper`: must be rejected.
- `accepted_result_on_superseded_current_target`: must not remain current.
- `first_node_pm_gate_stale_blocker`: must converge to one current blocker or
  a current PM packet, not a hidden bypass.

## Validation

Focused validation must include:

- Runtime unit tests for strict packet outcome and PM decision parsing.
- Runtime unit tests for same-family blocker retirement and final preflight.
- FlowGuard control-plane friction checks and model-test alignment.
- Entry-point/install checks that reject formal old compatibility surfaces.
- Background meta/capability regressions with inspected artifacts before final
  pass claim.

## Non-Goals

- No compatibility migration that keeps old aliases valid.
- No fallback parsing for prose, nested wrappers, or summary fields.
- No new ledger authority separate from the current packet/result/blocker/gate
  records.
- No remote push or release publishing without a separate user request.
