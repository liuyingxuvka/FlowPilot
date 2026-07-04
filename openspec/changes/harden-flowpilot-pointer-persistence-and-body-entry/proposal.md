## Why

FlowPilot currently treats `.flowpilot/current.json` and `.flowpilot/index.json`
as critical control-plane pointers, but the new-run shell still writes them by
direct file replacement rather than the existing Router JSON atomic write lane.
External corruption or a mid-write interruption can therefore turn the pointer
files into unreadable JSON and hard-fail ordinary `status` and
`final-preflight` commands.

The same incident class exposed a second entry weakness: `submit-result --body`
is accepted at the CLI as an opaque string, so PowerShell quoting can produce a
payload that looks like JSON to a human but arrives as a JSON string or
malformed text rather than a top-level JSON object.

## What Changes

- Route `.flowpilot/current.json` and `.flowpilot/index.json` writes through the
  existing Router JSON atomic write, lock, replace, fsync, and readback
  discipline.
- Add current-contract pointer recovery for corrupt current/index files only
  when the correct run can be proven without guessing.
- Preserve the existing current/index JSON shapes. This change does not add
  new business fields to `current.json` or `index.json`.
- Keep corrupt pointer backups as diagnostic residues only; they are not
  runtime authority and are not written back into pointer files.
- Add CLI-level `submit-result` body validation requiring a top-level JSON
  object, and add `--body-file` as the preferred PowerShell-safe entry path.
- Update runtime-kit prompt/card wording to prefer `--body-file` and to stop
  encouraging raw command-line JSON paste as the default.
- Extend the existing FlowGuard Cartesian/control-contract/test coverage
  models so pointer corruption and pseudo-JSON body entry are generated,
  owned, aligned, and consumed by current evidence.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `runtime-ledger-persistence`: extend existing atomic JSON persistence
  discipline to top-level FlowPilot pointer/catalog files.
- `active-writer-settlement`: treat current/index pointer locks, transient
  incomplete reads, dead writers, and stale corrupt targets through the existing
  settlement rules.
- `flowpilot-invocation-intent-isolation`: make pointer recovery preserve the
  rule that the current pointer is UI focus only and never startup/resume
  intent.
- `packet-open-authority-exits`: make `submit-result` body entry reject
  malformed, non-object, or stringified JSON before packet result mutation.
- `flowpilot-prompt-boundary-policy`: update common prompt/card return policy
  so formal outputs prefer `--body-file`.
- `end-to-end-chaos-coverage-matrix`: require Cartesian/model coverage for
  pointer corruption and body-entry fault combinations.
- `flowguard-test-obligation-ownership`: bind the new Cartesian/model
  obligations to ordinary tests, TestMesh, and Model-Test Alignment evidence.

## Impact

- Runtime code under `skills/flowpilot/assets/flowpilot_core_runtime/`.
- CLI entrypoints in `skills/flowpilot/assets/flowpilot_new_cli.py` and
  `skills/flowpilot/assets/flowpilot_new_run_commands.py`.
- Runtime-kit prompts and generated cards under
  `skills/flowpilot/assets/runtime_kit/`.
- FlowGuard models, result artifacts, and test ownership under `simulations/`
  and `tests/`.
- OpenSpec evidence, topology, local installed FlowPilot skill sync, and local
  git history.
