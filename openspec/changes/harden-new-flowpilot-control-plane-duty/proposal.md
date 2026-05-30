## Why

Recent live FlowPilot runs exposed a control-plane model miss: the new black-box runtime can pass scoped fake rehearsals while the foreground Controller still sees ambiguous nonterminal work, PM repair prose can be misparsed into the opposite lifecycle decision, and status/patrol reads can accidentally affect guard history. This needs a small bottom-logic repair now because the same failure class applies symmetrically to PM, reviewer, validator, FlowGuard, closure, and node-routing packets.

## What Changes

- Add a new-runtime control-plane duty contract that classifies each next action as router-internal, role wait, controller-external, user-required, recovery/blocker, or terminal.
- Add a bounded `run-until-wait`/process loop for the new runtime so safe router-internal mechanics are folded before the foreground Controller is asked to wait or dispatch a role.
- Harden PM repair decision parsing so hard lifecycle decisions come from structured decision fields, not incidental rationale words such as `block`, `blocked`, or `stop`.
- Enforce a single-source lifecycle invariant: a blocker cannot be both stopped and under repair, and stopped blockers cannot be silently ignored while repair packets continue.
- Make public status read-only for guard history and events; patrol remains the explicit state-refresh command.
- Add FlowGuard/model and ordinary regression coverage for adversarial PM prose, internal-action folding, short internal wait versus 60-second role patrol, stopped-blocker consistency, and status read-only behavior.

## Capabilities

### New Capabilities
- `new-flowpilot-control-plane-duty`: Covers new-runtime action classification, internal mechanical folding, structured repair decisions, read-only status, blocker lifecycle consistency, and foreground waiting boundaries.

### Modified Capabilities
- `runtime-ledger-persistence`: Status and patrol persistence requirements change so status is projection-only while patrol is the explicit guard-refresh path.
- `multiround-fake-ai-control-rehearsal`: Fake rehearsals must drive the same public control surface and include adversarial decision prose, not only direct runtime internals.
- `known-friction-regression-gates`: Known live-run friction now includes the parser/action-folding/status-readonly model-miss family.

## Impact

- Affected code: `skills/flowpilot/assets/ai_project_runtime/runtime.py`, `run_shell.py`, `flowpilot_new.py`, `fake_e2e.py`, and focused tests/simulations.
- Affected behavior: new FlowPilot runs keep the small black-box runtime, but internal mechanical work is folded before foreground duty, hard PM repair decisions require structured fields, and status no longer mutates guard history.
- Dependencies: real FlowGuard remains required; no old Router daemon or old monitor UI is restored.
