## Why

The current FlowPilot runtime now uses runtime-requested role bindings through
host-supported mechanisms, but several user-visible and agent-facing language
surfaces still describe old background-agent or fixed crew concepts. Those
phrases can bias future agents and users toward historical topology rather than
the current requested-role binding contract.

## What Changes

- Replace startup UI labels that say "background agents" and "six-role crew"
  with softer runtime role assistance wording.
- Replace active startup activation checklist wording that asks for a fixed
  role-slot count with runtime-requested binding coverage or explicit fallback
  evidence.
- Update public protocol and handoff text that still describes fixed crew
  recovery as current authority.
- Update reference protocol wording from sub-agent/spawn terminology to
  addressed role binding and open/reuse terminology where the text is active
  guidance.
- Keep internal schema and historical records unchanged unless a prompt or
  public guidance surface directly teaches the old concept.

## Capabilities

### Modified Capabilities
- `flowpilot-prompt-boundary-policy`: user-visible and active agent-facing
  surfaces must use runtime role binding language and avoid fixed crew or
  background-agent wording as current instruction.
- `runtime-requested-role-bindings`: startup and recovery documentation must
  describe role assistance as host-supported bindings requested by runtime
  responsibility, not as a fixed live cohort.

## Impact

- Startup intake UI source and preview copy.
- Active runtime startup activation card.
- Public protocol and repository handoff guidance.
- FlowPilot skill reference docs.
- Install/prompt scans and focused prompt/card validation.
- Installed FlowPilot skill synchronization after validation.
