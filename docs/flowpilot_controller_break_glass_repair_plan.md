# FlowPilot Controller Break-Glass Repair Plan

## Purpose

Controller break-glass is a narrow development-mode emergency lane for
FlowPilot control-plane failures. It exists for cases where the normal
Controller/Router/PM/control-blocker/packet repair channel is itself broken and
cannot produce a legal next action.

This is not ordinary project repair authority.

## Trigger Boundary

Break-glass may be opened only when current-run evidence shows one of:

- Router status and Controller action ledger are stuck, looping, or
  contradictory;
- Router cannot produce a legal next Controller action;
- a control blocker exists but PM repair or packet routing cannot legally
  handle it;
- a prompt/card asks for a return event that Router does not currently allow;
- manifest, contract, control-transaction registry, card, or schema surfaces
  contradict each other;
- the same control-plane blocker repeats after the normal retry or PM route
  cannot form a valid next action.

Break-glass must not be used for target-project bugs, worker defects, reviewer
quality findings, ordinary test failures, acceptance changes, route changes,
publishing, deployment, accounts, secrets, or private data.

## Prompt Placement

The full playbook lives at:

`skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`

The playbook is registered in `runtime_kit/manifest.json` as
`controller.break_glass_repair`.

A short reminder is repeated in Controller's operational surfaces:

- `runtime/controller_action_ledger.json.controller_table_prompt`;
- `runtime/router_daemon_status.json.break_glass_reminder`;
- `controller-patrol-timer` output;
- `continuous_controller_standby` payload.

This keeps the rare emergency path visible during long runs without turning it
into normal Controller work.

## Records

Break-glass records live under:

`.flowpilot/runs/<run-id>/controller_break_glass/`

The directory contains:

- `index.json`;
- `incidents/<incident-id>.json`;
- `patches/<patch-id>.json`.

Incident records capture trigger proof, normal lanes checked, control-plane
sources inspected, suspected FlowPilot defect, allowed reads/writes, forbidden
actions, validation plan, and exit criteria.

Patch records capture touched paths, temporary compensation, validation
evidence, rollback notes, final disposition, and whether a permanent root fix is
needed.

Incidents may leave open status only through an explicit closure path:

- a linked Recovery Supervisor transaction that is already closed;
- validated patch closure where success dispositions have closed validation
  evidence and no `not_run` validation placeholders;
- diagnostic-only closure when no patch was used;
- weak-evidence quarantine;
- explicit blocked/manual-repair disposition.

## Completion Boundary

Break-glass can restore the control channel, but it cannot close route gates,
approve PM/reviewer/FlowGuard operator decisions, mutate routes, or create target-project
evidence. After the control channel is healthy enough to produce a legal next
action, Controller must return to Router daemon status and Controller action
ledger processing.

Terminal closure or user-facing completion must disclose current-run
break-glass incidents through the FlowPilot skill improvement report or closure
summary.
