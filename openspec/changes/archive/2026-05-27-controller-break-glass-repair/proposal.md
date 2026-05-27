## Why

Long FlowPilot runs can still stall when the control plane itself is broken:
Router cannot produce a legal next action, Controller/PM/packet repair cannot
route, or prompt/contract/schema surfaces contradict each other. Routing every
repair through the same broken PM/control-blocker path can deadlock the run and
hide the underlying FlowPilot defect until much later.

## What Changes

- Add a Controller break-glass repair playbook for development-mode recovery
  from FlowPilot control-plane failures only.
- Surface a short, restrictive break-glass reminder in Controller's repeated
  operational surfaces: the generated Controller table prompt, daemon monitor
  status, patrol timer output, and continuous standby payload.
- Add run-scoped break-glass incident and temporary patch ledgers so every
  emergency action records trigger evidence, allowed scope, validation, rollback
  path, and final disposition.
- Add executable FlowGuard coverage that rejects ordinary project bugs,
  available normal PM repair, sealed-body access, gate approval, route mutation,
  or unrecorded temporary patching through the break-glass lane.
- Update documentation, templates, install checks, and focused runtime tests so
  the new lane stays visible but narrow.

## Capabilities

### New Capabilities

- `controller-break-glass-repair`: Defines Controller's narrow emergency lane
  for FlowPilot control-plane failures, including trigger proof, forbidden
  powers, incident/patch ledgers, validation, exit, and final reporting.

### Modified Capabilities

- `controller-ledger-table-prompt`: Repeated Controller work-board prompts must
  include a short break-glass reminder and playbook path without encouraging
  use for ordinary project defects.
- `controller-patrol-timer`: Patrol timer and standby monitor outputs must show
  the same narrow reminder when Controller is watching a live run.
- `blocker-repair-policy`: Normal PM/control-blocker repair remains the default,
  and break-glass is allowed only when the normal control repair lane itself is
  unavailable or contradictory.

## Impact

- Affected prompt cards: Controller core card and new system playbook under
  `skills/flowpilot/assets/runtime_kit/cards/system/`.
- Affected runtime surfaces: `flowpilot_router.py` Controller ledger prompt,
  daemon status, standby payload, and patrol timer output.
- Affected run templates and schema docs: run-scoped
  `.flowpilot/runs/<run-id>/controller_break_glass/` incident and patch ledgers.
- Affected validation: new focused FlowGuard model/check, runtime tests for
  reminder visibility and forbidden break-glass powers, OpenSpec validation,
  install check, local install sync, and local git commit readiness.
- No release, push, deployment, public API break, new dependency, or ordinary
  target-project repair authority is introduced.
