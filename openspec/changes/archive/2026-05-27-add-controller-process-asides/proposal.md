## Why

FlowPilot currently protects formal work through sealed packets, result bodies,
role-output envelopes, and Router-owned waits, but long-running roles can still
feel operationally invisible to Controller. Operators then have to inspect
several ledgers and status projections to learn whether a role is alive,
working, retrying a mechanical submission, or already submitted a formal
output.

This change adds a short Controller-facing process aside so roles can report
process state without leaking formal work content or creating a second
decision channel.

## What Changes

- Add an optional `controller_aside` surface to relevant packet, result, and
  role-output envelope/status flows.
- Repeat the aside rules in current work surfaces, not only in role core cards,
  so long-running work keeps the reminder visible.
- Allow roles to write one to three short natural-language process notes for
  Controller about workflow state, submission state, mechanical blockers,
  waiting, or recovery.
- Keep formal work content, evidence, conclusions, recommendations, approvals,
  route decisions, and report reasons out of the aside field.
- Make the Router preserve and expose the aside as Controller-visible process
  context only; Router must not inspect it for meaning, use it as formal
  evidence, or advance gates from it.
- Keep Worker-to-Worker communication forbidden; Controller is the only
  recipient of worker process asides.

## Capabilities

### New Capabilities
- `controller-process-asides`: Optional Controller-facing process notes on
  FlowPilot packet/result/role-output surfaces, with explicit non-authority
  boundaries.

### Modified Capabilities
- `controller-user-status`: Controller may use process asides to explain
  operational status without exposing formal work content.

## Impact

- Runtime prompts and card text for Controller, PM, reviewer, officers, and
  workers.
- Packet/result/role-output metadata surfaces that already create
  Controller-visible status packets or envelopes.
- FlowGuard model and focused tests that prove process asides cannot substitute
  for formal outputs, evidence, approvals, or Router events.
- Local FlowPilot install sync and install audit after repository validation.
