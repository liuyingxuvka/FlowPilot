# Design

## Target Structure

The split keeps the existing `flowpilot_router_io.py` module as the public and
private compatibility facade.

| Owner | Responsibility |
| --- | --- |
| `flowpilot_router_io_paths.py` | UTC helpers, skill/runtime-kit paths, bootstrap state paths, project-relative paths, runtime entrypoint references |
| `flowpilot_router_io_locks.py` | Runtime JSON write-lock constants, liveness classification, takeover/cleanup logs, writer-settlement helpers |
| `flowpilot_router_io_json.py` | Atomic JSON write, JSON read variants, daemon-critical JSON corruption handling, runtime-scan JSON reads |
| `flowpilot_router_io_hashes.py` | JSON hashing and role-output semantic hash helpers |
| `flowpilot_router_io.py` | Compatibility exports only |

## FlowGuard Function Blocks

Each block is modeled as `Input x State -> Set(Output x State)`:

| Function block | Input x State | Output x State |
| --- | --- | --- |
| Path resolution | `(project_root, run_root, state) x filesystem` | `{resolved_path, error} x filesystem` |
| Runtime JSON lock classification | `(target_path, lock_file) x filesystem/process_liveness` | `{classification, takeover_allowed, active, diagnostics} x unchanged filesystem` |
| Atomic JSON write | `(target_path, payload) x filesystem/lock_state` | `{write_success, wait_error, corruption_error} x updated JSON file and lock/takeover logs` |
| Runtime JSON read | `(target_path) x filesystem/lock_state` | `{payload, empty, write_in_progress, corruption_error} x unchanged filesystem` |
| Role-output hash | `(output_path) x filesystem` | `{raw_hash, semantic_hashes, none} x unchanged filesystem` |

## Compatibility

`flowpilot_router_io.py` imports from all child owners and exports the same
symbol set that existing router, packet, card, tests, and scripts use today.
The split must preserve object identity where tests compare imported functions.

## Validation Strategy

- compile/import smoke for parent and child modules;
- focused boundary tests for runtime JSON helper round-trip and child export
  identity;
- focused daemon/terminal runtime tests that exercise JSON write-lock liveness,
  takeover, cleanup, wait, and corruption behavior;
- FlowGuard router facade split, StructureMesh, and model-test alignment
  checks;
- background router tier plus background Meta and Capability regressions;
- install sync and install freshness checks.

## Risk Controls

- No lock semantic changes are allowed in this pass.
- Parent facade remains in place.
- Child modules stay below the runtime owner threshold.
- Skipped, timed out, or progress-only checks are reported as skipped, not pass
  evidence.
