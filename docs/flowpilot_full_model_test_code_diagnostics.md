# FlowPilot Full FlowGuard Model Coverage Inventory

## Claim Boundary

This inventory proves that FlowGuard model/check entrypoints were enumerated and classified against current evidence. Scoped replay or skipped checks remain blocking unless the replay evidence manifest attaches them to exact current runtime or source evidence.

## Summary

- Runner count: `140`
- Sweep ok: `false`
- Model-test alignment ok: `true`
- Source audit ok: `true`
- Full coverage ok: `true`
- Release convergence ok: `true`
- Deferred structure split count: `0`
- Unresolved non-deferred gap count: `0`
- Finding count across sweep records: `140`

## Prioritized Gap Groups

| Gap class | Runner count | First runners |
| --- | --- | --- |
| runner_unparsed_or_unavailable | 1 | flowpilot_process_liveness |
| runner_not_ok | 1 | flowpilot_final_confidence_gate |
| live_runtime_or_state_findings | 1 | flowpilot_model_mesh |

## Not-OK Or Unparsed Runners

| Runner | Issue | Mode | Notes |
| --- | --- | --- | --- |
| flowpilot_final_confidence_gate | not_ok | executed_read_only | runner_not_ok |
| flowpilot_process_liveness | unparsed | executed_read_only | runner_unparsed_or_unavailable |

## Evidence Notes

- `source_audited_alignment` means the runner is consumed by the current FlowGuard model-test alignment plan.
- `ordinary_test_text_reference` is weaker: it means the test corpus mentions the runner/model key, not necessarily that every boundary is asserted.
- `abstract_without_detected_ordinary_test_reference` is not present in the current inventory; baseline missing ordinary-test references are now owned by the focused coverage-gap tests.
- `missing_or_scoped_replay_adapter` means a replay gap is still blocking unless `covered_skipped_checks` attaches it to exact replay evidence.
- `supporting_model_owned` means the runner is an explicitly registered supporting model tier, not an unknown model boundary.
