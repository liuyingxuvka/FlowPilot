## Why

Controller can currently be woken while FlowPilot is still waiting and continue
to report a wait even when the formal runtime has already received an ACK,
role output, packet result, or router-authored next-action notice. A short
`controller_aside` can make this worse by making a role believe it has told
Controller, while Controller is not allowed to treat that aside as evidence.

## What Changes

- Add a Controller wait receipt audit that runs whenever foreground Controller
  standby/patrol observes a nonterminal wait.
- Check formal receipt surfaces only: card return ledgers, role-output status
  and ledger entries, packet result envelopes, packet ledgers, Router events,
  and `controller_next_action_notice.json`.
- Classify waits into actionable outcomes: still waiting, formal return ready,
  formal return seen but Controller ledger stale, result envelope seen without
  next-action notice, aside-only completion claim, and malformed/stale return
  evidence.
- Preserve Controller authority boundaries: no sealed-body reads, no quality or
  sufficiency judgment, no progress from `controller_aside`, and no approval or
  route advancement from Controller inspection.
- Surface plain-language status only for meaningful user-facing outcomes such
  as control-plane stuck conditions, user-required action, blockers/recovery,
  terminal states, or explicit user status requests.
- Update OpenSpec, FlowGuard model coverage, runtime code, focused tests,
  background regression evidence, and the locally installed FlowPilot skill.

## Capabilities

### New Capabilities

- `controller-wait-receipt-audit`: Controller audits formal receipt surfaces
  during all waiting states without reading sealed work content.

### Modified Capabilities

- `controller-foreground-standby`: standby/patrol wakeups perform the wait
  receipt audit before continuing a quiet wait.
- `router-external-wait-reconciliation`: formal return evidence discovered
  during a wait is classified as released, stale, missing, or malformed instead
  of being treated as ordinary silence.
- `controller-process-asides`: `controller_aside` remains non-authoritative and
  may only prompt an audit of formal receipt surfaces.
- `controller-user-status`: user-visible waiting updates distinguish no formal
  return, formal return ready, control-plane stuck, and aside-only claims.

## Impact

- Affects Controller standby/patrol runtime, Controller status projections,
  wait reconciliation helpers, runtime prompts/cards, FlowGuard simulations,
  focused router/runtime tests, background meta/capability checks, and local
  installed skill synchronization.
