## Why

Controller break-glass is currently a narrow development escape hatch: it can
record incidents and temporary patches when the control plane cannot produce a
legal next action. That prevents ad hoc silent fixes, but it still leaves a
larger reliability gap: repeated control-plane failures can be repaired one at a
time without promoting the same defect family into a full FlowGuard-backed
recovery transaction.

The desired behavior is stronger. When FlowPilot hits a serious control-plane
failure, the normal Controller identity should be suspended and a temporary
Recovery Supervisor identity should take over. That identity can repair the
control plane, classify same-family blockers, optionally request audited scoped
body access when no role lane is available, then close the recovery transaction
and force a fresh Controller-core reinjection before normal route work resumes.

## What Changes

- Add a Recovery Supervisor layer above Controller break-glass.
- Record recovery transactions, control-plane blocker family entries, scoped
  body-access grants, and Controller reinjection records under the existing
  run-scoped `controller_break_glass` directory.
- Require recovery closure to include same-family repair evidence and a fresh
  Controller reinjection marker.
- Preserve the ordinary Controller body boundary by treating any emergency body
  access as a Recovery Supervisor grant, never a normal Controller permission.
- Add a focused FlowGuard model and regression tests for identity transition,
  same-family repair, audited body access, and reinjection before resume.

## Capabilities

### Modified Capabilities

- `controller-break-glass-repair`: Introduces the temporary Recovery Supervisor
  identity and recovery transaction ledger.
- `blocker-repair-policy`: Binds current and historical control-plane blockers
  to defect-family repair decisions.
- `controller-boundary-core-load`: Requires a fresh Controller-core boundary
  confirmation after Recovery Supervisor exit.

## Impact

- `skills/flowpilot/assets/flowpilot_controller_break_glass.py`
- `skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`
- `simulations/flowpilot_recovery_supervisor_model.py`
- `simulations/run_flowpilot_recovery_supervisor_checks.py`
- `tests/test_flowpilot_controller_break_glass.py`
- OpenSpec deltas under this change.
