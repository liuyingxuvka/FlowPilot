## Overview

This is a behavior-preserving structure reduction. The implementation will
keep old entrypoints intact and move responsibilities behind thin wrappers in
small, reversible slices. The refactor is allowed to change module layout and
call structure; it is not allowed to change protocol semantics, JSON shapes,
event names, persisted state meaning, release scope, or install behavior.

## Baseline

- Baseline commit: `2215a65cc8a293ae24684e9d9b32d486c9cf32fd`.
- Baseline version: `0.9.6`.
- Rollback point: the branch starts from the baseline commit; no tracked backup
  copy of the 39k-line router is added because git history is the authoritative
  source-of-truth backup.
- Baseline validation:
  - `python scripts\check_install.py --json` passed.
  - `python -m unittest tests.test_flowpilot_router_runtime_controller tests.test_flowpilot_router_runtime_ack_return tests.test_flowpilot_router_runtime_closure tests.test_flowpilot_user_flow_diagram` passed, 44 tests.

## Risk Intent

- Prevent broad rewrites that mix behavior changes into structure movement.
- Prevent new module boundaries from bypassing router state save, ledger,
  prompt-isolation, packet-body, or idempotency rules.
- Preserve event names and payload shapes while moving handler code.
- Preserve controller action ordering while splitting provider functions.
- Preserve action application side effects while moving low-risk handlers.
- Preserve Meta/Capability model result meaning while introducing phase
  functions.
- Preserve `check_install.py` JSON compatibility while splitting check groups.
- Keep each slice independently testable and revertible.

## Sequence

1. Freeze baseline and write structural audit evidence.
2. Add the focused structural-refactor FlowGuard model and run it.
3. Split event entry handling into a helper module while leaving
   `_record_external_event_unchecked` as a compatibility wrapper.
4. Split `compute_controller_action` into ordered provider helpers and add an
   ordering test.
5. Split selected `apply_controller_action` branches into action handlers and
   add handler tests.
6. Split large router runtime tests into domain wrappers while preserving the
   legacy aggregate test file.
7. Move selected router runtime domains into helper modules one domain at a
   time, starting with route mutation/route activation because current focused
   tests already cover it.
8. Split Meta and Capability model `apply` functions into named phase helpers,
   then rerun the corresponding checks and compare headline result counts.
9. Split `scripts/check_install.py` into check-group helpers while preserving
   output.
10. Update docs, install the source-owned `flowpilot` skill locally, run public
    boundary checks, commit, and push the work branch.

## Compatibility Strategy

- Public router functions remain importable from `flowpilot_router.py`.
- New modules may import the existing router module during transitional slices;
  later slices can reduce that coupling only after tests prove behavior is
  unchanged.
- For moved code, the first pass favors exact extraction over cleanup.
- New tests assert dispatch/provider/handler ordering and entrypoint
  compatibility rather than changing business expectations.

## Validation Strategy

- Focused tests after each slice that touches runtime behavior.
- `python -m py_compile` for changed Python modules.
- `openspec validate behavior-preserving-router-structure-reduction --strict --json`.
- Focused FlowGuard structural refactor model/check runner.
- Router-loop, route mutation, controller-action, card/ACK, closure, startup,
  resume, and user-flow tests as appropriate to touched boundaries.
- Meta and Capability checks after their model files are split.
- `python scripts\check_install.py --json`.
- `python scripts\check_public_release.py --json` before remote sync.
- `python scripts\install_flowpilot.py --sync-repo-owned --json` and
  `python scripts\audit_local_install_sync.py --json`.

## Out Of Scope

- New FlowPilot features.
- Protocol field additions/removals or JSON shape changes.
- Replacing FlowGuard or introducing a fake modeling layer.
- Release tags, GitHub releases, deployment, or publishing companion skills.
- Deleting compatibility entrypoints before downstream users have migrated.
