## Why

The new black-box FlowPilot runtime exists, but a fresh formal `Use FlowPilot`
invocation still needs a direct new-system entrypoint. The desired product is
not an old-system migration: it is a new FlowPilot that reuses only the native
startup intake UI and then runs through the new current-run ledger, router,
dynamic leases, FlowGuard work orders, review, validation, and closure.

## What Changes

- Add a new formal entrypoint for fresh FlowPilot runs:
  `skills/flowpilot/assets/flowpilot_new.py`.
- Keep the old startup UI as the only reused UI surface for formal launch.
- Treat old `flowpilot_router.py` as diagnostic/reference material for old
  runs, not the fresh-run authority.
- Add a FlowGuard model for the new entrypoint path from `Use FlowPilot` to
  final closure.
- Add end-to-end rehearsal tests that prove the new entrypoint can create a
  run, record sealed startup intake, issue the first PM packet, exercise
  dynamic leases, run targeted FlowGuard, review, validate, and close.

## Impact

- Fresh `Use FlowPilot` instructions in `skills/flowpilot/SKILL.md` now point
  at `flowpilot_new.py start`.
- The old startup UI remains intact and is launched by the new entrypoint.
- No new monitoring UI is required.
- Install inventory, version, changelog, tests, and FlowGuard evidence are
  updated for the new formal entrypoint.
