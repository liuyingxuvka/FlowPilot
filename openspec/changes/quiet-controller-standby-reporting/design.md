## Context

The Router daemon owns ordinary FlowPilot progress through daemon status and the Controller action ledger. Its internal tick is intentionally fast and must remain unchanged. The noisy behavior is the foreground Controller's standby patrol loop and user-facing reporting behavior during quiet waits.

Today the skill and role cards instruct Controller to run `controller-patrol-timer --seconds 10` whenever it reaches `continuous_controller_standby`. Existing specs already prevent Controller from exiting while FlowPilot is active, and they already require plain language. They do not clearly separate "plain language" from "do not speak unless useful."

## Goals / Non-Goals

**Goals:**

- Make quiet Controller standby less noisy by defaulting the patrol timer to 60 seconds.
- Keep Router daemon progress and heartbeat/liveness semantics unchanged.
- Add a speak/silence rule for Controller user reports.
- Keep process asides useful for Controller operational context without turning them into user chatter.
- Validate with FlowGuard, targeted runtime tests, install checks, and background broad regression evidence.

**Non-Goals:**

- Do not slow the Router daemon's one-second tick.
- Do not remove continuous Controller standby or weaken anti-exit gates.
- Do not create a new display mechanism, status template, or route-sign system.
- Do not broaden Controller authority to read sealed bodies, approve gates, or drive route progress from status text.

## Decisions

1. **Change only foreground quiet patrol cadence.**
   - Decision: set `CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS` and generated patrol command surfaces to 60 seconds.
   - Rationale: this directly reduces foreground wakeups while preserving daemon-owned progress.
   - Alternative rejected: slowing daemon tick, because that could delay real progress and blur daemon liveness semantics.

2. **Make speak/silence policy explicit.**
   - Decision: Controller may report only meaningful user-facing changes: user action required, blocker/recovery, terminal result, state transition, explicit user status request, or required display text.
   - Rationale: plain wording alone does not prevent low-value messages.
   - Alternative rejected: adding another generated summary field, because earlier user-language guidance intentionally avoided a new display mechanism.

3. **Keep process asides internal by default.**
   - Decision: process asides may inform Controller's operational understanding but are not automatically relayed to users.
   - Rationale: asides are short process notes, not formal work content or user-facing evidence.

4. **Model before broad confidence.**
   - Decision: update focused patrol and process-aside/status obligations before claiming runtime completion.
   - Rationale: this project requires real FlowGuard and treats skipped or progress-only checks as scoped, not passed.

## Risks / Trade-offs

- New Controller work may be noticed up to 60 seconds later during a quiet standby interval. Mitigation: only quiet standby is slowed; already-ready ledger work still preempts waits when checked.
- Too much silence could make users think FlowPilot stopped. Mitigation: terminal, blocker, recovery, user-required, and explicit status-request cases still produce concise user-facing updates.
- Prompt/runtime drift could leave some surfaces at 10 seconds. Mitigation: update skill docs, role/resume cards, generated table prompt data, tests, and local installed copy together.
- Broad model regressions may be slow. Mitigation: run heavyweight suites in the documented background log directory and inspect completion artifacts before claiming broad pass.
