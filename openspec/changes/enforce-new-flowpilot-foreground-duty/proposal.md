## Why

The new FlowPilot runtime can record a nonterminal `next_action` and a
`lifecycle_guard` snapshot, but the live foreground Controller can still treat
a scoped closure or quiet wait as a place to return control to the user. This
change closes that boundary: every nonterminal state must expose an executable
foreground duty, including waits, and terminal return must require explicit
stop authority.

## What Changes

- Add a new foreground duty layer for the new `flowpilot_new.py` runtime.
- Convert passive waits into explicit duty actions such as timed patrols.
- Add a hard pre-final gate so the foreground Controller cannot claim done,
  stop, or return terminal output unless `controller_stop_allowed` is true.
- Keep the new runtime clean: dynamic leases remain the authority, and the old
  Router daemon, old monitoring UI, fixed six-person topology, and legacy
  compatibility surfaces do not become required new-runtime dependencies.
- Clean up misleading terminology so status display, Cockpit/startup display,
  old monitor/kanban behavior, lifecycle guard, and foreground duty are named
  as separate concepts.
- Add FlowGuard and ordinary regression coverage for the observed miss: scoped
  closure opens or exposes later work, the guard blocks stop, and the foreground
  duty loop continues or enters a timed patrol instead of ending.

## Capabilities

### New Capabilities
- `new-flowpilot-foreground-duty`: Defines the new runtime foreground duty
  contract, including hard final-return gating, explicit timed wait patrols,
  scoped-closure continuation, recovery classification, and terminology
  boundaries.

### Modified Capabilities
- `runtime-ledger-persistence`: Persist duty snapshots and patrol history as
  metadata derived from the canonical new-runtime ledger.
- `multiround-fake-ai-control-rehearsal`: Extend fake-host rehearsals to cover
  the live foreground boundary, not only the internal router driver.

## Impact

- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/flowpilot_new.py`
- `skills/flowpilot/assets/ai_project_runtime/*`
- FlowGuard model and rehearsal scripts under `simulations/`
- Focused unit tests under `tests/`
- Local installation sync and audit scripts/results
