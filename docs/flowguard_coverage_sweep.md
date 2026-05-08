# FlowGuard Coverage Sweep

Use `scripts/run_flowguard_coverage_sweep.py` when deciding whether a finding
means "fix runtime", "fix check flow", or "extend a model".

The sweep is read-only by default:

```powershell
python scripts\run_flowguard_coverage_sweep.py
```

It does not pass `--json-out` to model runners. Runners that still write result
files by default are not executed; the sweep reads their last persisted JSON
result instead and marks the runner record with `read_only_mode:
read_existing_result`.

## Ledger Fields

Each runner is summarized into the same surface:

- `abstract`: Explorer, safe-graph, scenario, or static model checks.
- `progress`: stuck, loop, terminal reachability, or nontermination checks.
- `hazards`: explicit negative scenarios or hazard states.
- `source`: source-file audits or conformance source scans.
- `live`: current `.flowpilot` run or runtime-state audits.

Every emitted finding receives a classification:

- `modeled_current_live_hit_fix_runtime_or_current_state`: the model already
  covers the issue and the current run hits it. Fix runtime/current state first.
- `modeled_source_hit_fix_source_or_runtime`: source audit is already modeled.
  Fix source/runtime first.
- `abstract_or_runner_failure_review_check_flow`: a model or runner failed
  outside a live/source finding. Inspect the check flow before changing runtime.
- `boundary_expected_or_informational`: expected blockers, skipped checks, or
  nonblocking evidence.

## Current Interpretation

For `run-20260508-064618`, the sweep should still surface the stopped
historical control-plane live-run findings as
`modeled_current_live_hit_fix_runtime_or_current_state`. Treat those as evidence
that the model covers the old failure shape, not as proof that newly generated
runtime artifacts are broken.

Use `simulations/run_flowpilot_repair_transaction_checks.py` whenever a runtime
change affects blocker repair, packet reissue, reviewer recheck, or router
resolution. It models the intended architecture: PM repair opens a transaction,
packet generation commits atomically, success and non-success reviewer outcomes
are routable, and terminal success or follow-up block states refresh visible
authorities together. Runtime conformance for that architecture is covered by
the FlowPilot router tests.
