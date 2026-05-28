# FlowGuard-First Work Order Grounding

Date: 2026-05-28

## Task

Adopt a FlowGuard-first decision core for FlowPilot while preserving the
existing Router, packet, role-authority, ledger, and install-sync shell.

## Existing Model Preflight

- Existing broad owners: `simulations/meta_model.py` and
  `simulations/capability_model.py` already model FlowPilot's formal route,
  FlowGuard modeling coverage, role-scoped work, child-skill projection,
  test obligations, reviewer gates, and final closure.
- Existing spec owners:
  - `flowguard-modeling-coverage`
  - `flowguard-test-obligation-ownership`
  - `role-child-skill-use`
  - `flowpilot-prompt-boundary-policy`
- Reuse decision: extend the existing model/spec family with one focused child
  boundary for FlowGuard work-order/report traceability instead of creating a
  parallel process framework.

## Development Process Flow

- Stage 1: OpenSpec proposal/design/specs/tasks define the new work-order and
  report protocol.
- Stage 2: Prompt cards adopt the shared vocabulary while preserving current
  Router-authorized runtime paths and sealed-body limits.
- Stage 3: Focused card tests and a focused FlowGuard model prove the new role
  obligation chain.
- Stage 4: Heavy meta/capability regressions run through background artifacts
  after source edits are stable.
- Stage 5: Local installed FlowPilot is synchronized and audited only after the
  source tree is ready.

## FlowGuard Route Choice

Use a focused child model for this change because the parent models are broad
and the current dirty worktree already contains peer-generated result updates.
The child model should check the new obligation chain directly:

- PM cannot make major non-trivial decisions without a current work-order
  report or scoped non-required reason.
- Officers answer work orders but do not approve gates.
- Reviewers block missing, stale, wrongly scoped, progress-only, or unaccepted
  reports.
- Workers return packet-scoped FlowGuard obligation coverage and do not mutate
  routes.
- Controller surfaces status only and does not interpret reports.

## Evidence Boundary

This record is grounding evidence only. Passing evidence for the implementation
must come from OpenSpec validation, focused card tests, the focused FlowGuard
model check, targeted runtime tests where applicable, background regression
artifacts, and install-sync audit results.
