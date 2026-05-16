## Context

The prompt-isolated FlowPilot router currently creates a run shell, starts role
slots, loads Controller core, and only then exposes
`create_heartbeat_automation` when scheduled continuation was requested. That
ordering lets the run function, but it blurs the boundary between startup host
bootstrap and Controller duties. The heartbeat is an external host side effect
that protects the Controller loop; it should be established before the router
declares the Controller core active.

## Goals / Non-Goals

**Goals:**

- Emit the first-time startup heartbeat host action before
  `load_controller_core`.
- Keep manual-resume startup runs free of heartbeat host actions.
- Keep Controller resume/recovery behavior intact for later wakes.
- Model and test the order so future route-loop changes cannot regress it.
- Preserve existing run-scoped files and continuation binding semantics.

**Non-Goals:**

- Redesign heartbeat resume rehydration.
- Change the one-minute heartbeat cadence.
- Change user startup intake questions or role-spawn policy.
- Publish, push, tag, or release the repository.

## Decisions

1. Treat startup heartbeat creation as a bootloader/host bootstrap boundary.

   The router should compute `create_heartbeat_automation` once run-scoped
   startup files and role slots exist, but before `load_controller_core`.
   This preserves the host proof requirement while keeping Controller core
   free from first-time continuation setup.

2. Keep heartbeat binding persisted through the same action and payload.

   The action type, expected payload, `continuation_binding.json`, and
   `continuation_binding_recorded` flag stay compatible. Only the action actor,
   label/summary wording, allowed reads, and ordering change.

3. Strengthen model and runtime tests around ordering rather than relying on
   prose.

   The FlowGuard meta model should represent `controller_core_loaded` separately
   from first-time heartbeat creation and reject any scheduled-continuation path
   that loads Controller before heartbeat binding is recorded. Runtime tests
   should assert the real router sequence.

## Risks / Trade-offs

- [Risk] Existing test helpers assume `boot_to_controller()` stops at
  `load_controller_core` without handling heartbeat.
  Mitigation: update only helper paths that simulate scheduled continuation so
  manual-resume flows stay unchanged.

- [Risk] The startup heartbeat action needs `router_state.json` before
  Controller core exists.
  Mitigation: create the initial run state earlier, during run-shell startup,
  and keep `load_controller_core` responsible for marking Controller entry and
  refreshing route memory.

- [Risk] Parallel AI edits touch the same router and model files.
  Mitigation: inspect current diffs before editing and make the smallest
  additive changes around heartbeat ordering.
