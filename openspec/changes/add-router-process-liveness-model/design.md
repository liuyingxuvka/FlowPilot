## Context

FlowPilot's current validation stack has two extremes. Meta/Capability checks
cover broad protocol gates but compress the Router loop mechanics that caused
recent bugs. Focused models preserve concrete mechanics but only cover one
boundary at a time. This change adds a middle-layer model for process liveness
and convergence.

## Goals / Non-Goals

**Goals:**

- Preserve the bug-prone control mechanics: tick settlement before next action,
  legal wait targets, event authority, blocker lanes, retry limits, PM repair
  returns, route mutation freshness, per-node reviewer coverage, and terminal
  ledger ordering.
- Keep the model fast by abstracting product content, packet body text, UI
  details, and child-skill internals.
- Produce executable evidence for safe graph coverage, no stuck/nonterminating
  states, known-bad hazard detection, and current-run process risk projection.

**Non-Goals:**

- Do not change Router runtime behavior.
- Do not replace focused models for daemon reconciliation, packet runtime,
  prompt boundaries, or router-loop mechanics.
- Do not claim Meta/Capability-level full protocol coverage.
- Do not open sealed packet/result bodies during current-run projection.

## Decisions

1. Model the process as a meso-level state machine rather than another
   stage-only full-flow model.
   - Rationale: speed should come from abstracting product semantics, not from
     collapsing the control mechanics that produced recent misses.
   - Alternative rejected: add more invariants to Meta/Capability only. Those
     checks are already too expensive for routine diagnosis.

2. Treat terminal outcomes as either `complete` or `controlled_blocked`.
   - Rationale: FlowPilot does not need every trace to succeed; it needs every
     nonterminal trace to converge to a safe terminal state with explicit
     evidence or blocker ownership.
   - Alternative rejected: require all traces to reach completion. Legitimate
     fatal protocol blockers and exhausted repair loops must be accepted as
     controlled stops.

3. Include hazards as first-class negative fixtures.
   - Rationale: the model should prove that old miss classes fail, not only
     that a happy path passes.
   - Alternative rejected: report only safe graph progress. A green graph alone
     can still be over-compressed.

4. Track route-node coverage with a compact bitmask instead of concrete product
   node bodies.
   - Rationale: the liveness question is whether every route node is reached,
     reviewed, ledgered, and included in final closure. The product meaning of
     each node belongs in focused runtime checks.
   - Alternative rejected: collapse all route work into one abstract node. That
     misses the skipped-node and premature-final-ledger class of bugs.

5. Classify blockers before selecting a handling lane.
   - Rationale: small local/reconciliation fixes should exhaust the local retry
     lane before PM repair, while route-scope and fatal protocol blockers need
     different handling.
   - Alternative rejected: model every blocker as a generic PM repair candidate.
     That can hide the exact misrouting class the user observed.

## Risks / Trade-offs

- [Risk] The model becomes too broad and duplicates Meta/Capability. Mitigation:
  keep product, UI, and child-skill content out of the state.
- [Risk] The model becomes too abstract and misses Router bugs again.
  Mitigation: explicitly model settlement, wait authority, blocker return, route
  mutation freshness, and terminal ledger convergence.
- [Risk] Current-run projection overclaims runtime safety. Mitigation: report it
  as process-risk projection only and keep focused/runtime checks authoritative
  for concrete implementation behavior.
- [Risk] Per-node coverage becomes expensive if it stores concrete node content.
  Mitigation: track only node index and review/completion masks.
