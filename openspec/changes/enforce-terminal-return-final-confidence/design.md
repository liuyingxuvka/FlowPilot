## Context

The current `final-confidence` tier aggregates refreshed control-plane, event-idempotency, model-test-alignment, and known-friction evidence. This proves broad repository-side confidence, but it does not prove that a formal FlowPilot run has reached `foreground_duty.action=terminal_return`.

The observed active run proves the gap: final-confidence evidence can pass while `flowpilot_new.py final-preflight` returns `allowed=false`, `controller_stop_allowed=false`, and `next_action:open_startup_intake`.

## Goals / Non-Goals

**Goals:**

- Add a fail-closed terminal-return evidence row to the final-confidence aggregation when exit authority is required.
- Preserve the current control-plane live audit as a health/currentness check, not a stop-authority check.
- Make the `final-confidence` test tier run the terminal-return gate by default for broad release/exit claims.
- Keep missing, blocked, startup-intake, and nonterminal preflight states visible in result JSON and TestMesh evidence.

**Non-Goals:**

- Do not auto-confirm, synthesize, or script startup intake.
- Do not add a new runtime authority path, ledger, packet kind, or compatibility shim.
- Do not make repository-side confidence impossible when a caller explicitly scopes out formal exit authority for diagnostic use.

## Decisions

1. **Add a separate terminal-return evaluator.**
   - Rationale: Control-plane live audit can be healthy while the run is correctly waiting for user-required startup intake. Folding stop authority into that row would blur two different claims.
   - Alternative considered: Make control-plane live audit fail when final-preflight is nonterminal. Rejected because nonterminal can be a valid current-run state for health audits.

2. **Execute `flowpilot_new.py final-preflight` through the final-confidence runner when terminal return is required.**
   - Rationale: The public formal-run authority is the `flowpilot_new.py` entrypoint. Reusing it prevents a parallel interpretation of lifecycle status.
   - Alternative considered: Read `.flowpilot/current.json` and infer terminal state directly. Rejected because status projection is display-only and the runtime already exposes a structured preflight.

3. **Allow diagnostic scoped confidence only by explicit opt-out.**
   - Rationale: Most broad completion claims need exit authority. A diagnostic run may still need repository evidence without a current FlowPilot run, but that must be visible as scoped evidence.
   - Alternative considered: Always require a live run. Rejected because repository release checks can be run outside a formal FlowPilot invocation.

4. **Bind TestMesh release mapping to the terminal-return gate.**
   - Rationale: Acceptance TestMesh already owns release child evidence. It should expose whether final-confidence includes formal exit evidence, so fake-AI/release paths cannot hide this missing leaf.

## Risks / Trade-offs

- Formal startup may be blocked by required native UI input -> The gate reports `open_startup_intake` as a blocker instead of fabricating intake evidence.
- Existing automation may call final-confidence without a live run -> Provide an explicit scoped opt-out for repository-only diagnostics and keep the default strict for release/exit claims.
- Adding another required evidence row can make broad checks fail more often -> This is intended when the claim includes Controller exit authority; local repository confidence remains separately reportable.
