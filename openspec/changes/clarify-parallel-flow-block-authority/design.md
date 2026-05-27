## Context

FlowPilot already stores run-local control state under each run root and treats
`.flowpilot/current.json` as UI focus/default-target metadata. The remaining
gap is the displayed active-set contract: when several runs or Flow blocks are
active, a checker must distinguish intentional parallelism from stale active
residue.

The user-facing intent is:

- A/B/C Flow blocks may run at the same time.
- A/B/C do not need one global main line.
- Live agents inside A belong to A, not to B or C.
- A user or controller operation must say whether it applies to A, B, C, or
  all selected blocks.
- Old or terminal residue must not appear as a live active block.

## Model

Represent the UI/status behavior as:

`UI event x UI state -> Set(UI output x UI state)`

Core UI states:

- `single_focus_run`: only one visible active run/block.
- `parallel_active_set`: multiple legal active runs/blocks with explicit
  `active_set_authority`.
- `block_scoped_agents`: one Flow block has multiple live agents under one
  parent block.
- `targeted_operation_pending`: an operation names one block/run or all selected
  blocks/runs.
- `stale_residue_quarantined`: old active-looking entries are present but
  classified as stale/history, not live work.
- `ambiguous_active_set`: multiple active entries are visible without explicit
  authority; this must fail validation.

## Data Contract

`active_ui_task_catalog` should expose:

- `authority: "explicit_active_set"`;
- `scope_kind`: `single_run`, `parallel_runs`, or `block_scoped_agents`;
- `current_pointer_is_ui_focus_only: true`;
- `global_main_required: false`;
- `operation_target_required: true`;
- `active_tasks[]` entries with `run_id`, `flow_block_id`, `target_id`,
  `target_scope`, `status`, `focus_selected`, `background_active`,
  `operation_target_allowed`, and `stale_residue`;
- `operation_targets` with `current_focus`, `all_active`, and per-run/block
  target ids;
- `hidden_non_current_running_index_entries` only for stale/history entries
  that are deliberately hidden from live work.

The route-state snapshot authority should mirror enough of this contract for
the FlowGuard live audit to prove explicit active-set authority without reading
private run bodies.

## Implementation Approach

1. Update the active UI task catalog builder to produce explicit active-set
   authority metadata and target identifiers.
2. Update route-state snapshots so background running entries include the same
   target/scope fields and stale-residue classification.
3. Update the control-plane friction live audit to accept legal explicit
   active sets and keep rejecting ambiguous active sets.
4. Add focused router runtime tests for:
   - A/B legal parallel runs with no global main line;
   - current focus as default target only;
   - targeted stop/continue metadata;
   - stale or terminal residue not counted as live active work.
5. Add model/matrix tests so missing target ids, missing authority metadata,
   or fake all-run operations fail.

## Risks And Mitigations

- Risk: overcorrecting into a single-main-line model. Mitigation: spec and tests
  explicitly require `global_main_required: false`.
- Risk: hiding real active work as stale residue. Mitigation: stale entries must
  carry explicit reason/source and remain auditable as history.
- Risk: UI wording exposes internal ids. Mitigation: user-facing status can use
  labels, but machine-readable status keeps target ids for safe operations.
- Risk: active-set tests race with peer agents. Mitigation: use isolated temp
  projects for runtime tests and treat the real `.flowpilot` live audit as
  read-only.

## Validation

- OpenSpec strict validation for this change.
- FlowGuard import preflight and control-plane friction checks.
- Focused tests for active UI task catalog and route-state snapshot projection.
- Model-test alignment refresh where active-set authority evidence is listed.
- Fast tier and background Meta/Capability regressions with final artifact
  inspection.
- Install sync and audit after source validation.
