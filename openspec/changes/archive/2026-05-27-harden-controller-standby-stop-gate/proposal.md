## Why

Foreground Controller standby can still be misread when a nonterminal status
projection says the turn may return to the user. A live Router daemon plus a
waiting `continuous_controller_standby` row must never be treated as permission
for the Controller to final-answer or stop.

## What Changes

- Split user-facing status return permission from Controller stop permission in
  standby, patrol, and status-summary payloads.
- Make the Controller action ledger and terminal stop gate the only authority
  for ending foreground Controller standby.
- Mark current status summaries as display projections and add freshness/source
  metadata so stale `next_step` projections cannot authorize Controller exit.
- Harden Controller-facing prompts and generated table text so nonterminal
  return modes mean "report or handle this duty, then stay attached", not
  "finish the Controller role".
- Add focused FlowGuard and runtime regression coverage for the known-bad case:
  live daemon, waiting `continuous_controller_standby`, nonterminal return
  signal, and stale/completed display action projection.
- Extend model-hierarchy coverage so full FlowGuard confidence includes every
  visible/user-triggerable branch or explicitly marks it disabled/out of scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `controller-foreground-standby`: foreground standby must distinguish
  status-update returns from Controller stop permission and must require
  reattach/patrol while a live daemon has nonterminal standby duty.
- `controller-patrol-timer`: patrol timer outputs must carry a final-answer
  preflight contract and reject nonterminal return signals as stop evidence.
- `controller-user-status`: current status summaries must be explicitly
  display-only projections with source/freshness metadata and non-authoritative
  `next_step` semantics.
- `flowguard-model-hierarchy`: full-model confidence must require an inventory
  and current evidence for visible/user-triggerable controls, buttons, status
  returns, recovery paths, and terminal/stop branches.

## Impact

- Affected runtime code: Controller standby snapshots, patrol timer payloads,
  current status summary builder, and display/status projection tests.
- Affected prompt surfaces: Controller role card, resume/reentry card,
  generated Controller table prompt, and related runtime prompt assets.
- Affected verification: focused FlowGuard patrol model/checks, targeted router
  runtime tests, model-hierarchy checks, install checks, local install sync,
  and background meta / capability regressions.
