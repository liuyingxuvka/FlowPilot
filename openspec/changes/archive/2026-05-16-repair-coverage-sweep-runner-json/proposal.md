## Why

`scripts/run_flowguard_coverage_sweep.py` can execute read-only runners that
support both `--json` and `--json-out`, but it only passed `--json` when a
runner did not mention `--json-out`. That made a JSON-capable runner emit its
human summary, so the sweep recorded an unparsed runner even when the runner
itself exited successfully.

## What Changes

- Treat `--json` support as the machine-output contract for read-only runner
  execution, independent of whether the runner also supports `--json-out`.
- Keep the sweep read-only: do not pass `--json-out`, and do not refresh
  existing result files during the sweep.
- Add regression coverage so JSON-capable runners with both flags are executed
  with `--json`.

## Impact

- Affected code: `scripts/run_flowguard_coverage_sweep.py`.
- Affected tests: `tests/test_flowpilot_maintenance_tools.py`.
- Affected behavior: coverage sweep no longer reports a false unparsed runner
  for JSON-capable read-only checks.
