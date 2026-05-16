## Boundary

This is a validation-plumbing repair, not a model or runtime behavior change.
The sweep remains read-only and continues to avoid `--json-out` so persisted
simulation result files are not refreshed as a side effect.

## Decision

Use the presence of `add_argument("--json"` as the signal that a runner can
print machine-readable output. If a runner also has `--json-out`, the sweep
still passes only `--json`; this captures JSON on stdout without writing any
result file.

## Risk

- If a runner advertises `--json` but prints non-JSON, the sweep still marks it
  unparsed. That is correct because the runner violated its machine-output
  contract.
- Runners that write result files by default remain excluded by the existing
  `_read_only_runnable` guard.
