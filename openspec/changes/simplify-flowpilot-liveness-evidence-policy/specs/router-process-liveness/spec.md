# router-process-liveness Spec Delta

## MODIFIED Requirements

### Requirement: Fast process model preserves Router control mechanics
FlowPilot SHALL provide a fast middle-layer FlowGuard model that abstracts
product content while preserving Router tick settlement, legal wait/event
authority, blocker lanes, retry bounds, PM repair returns, route mutation
freshness, terminal ledger convergence, and the unified ACK/progress liveness
evidence ladder.

#### Scenario: Unified liveness ladder converges
- **WHEN** the process liveness model explores waits before ACK, waits after
  ACK, progress reminders, valid progress recovery, and no-evidence
  replacement
- **THEN** every reachable nonterminal wait state can reach either continued
  patrol, current progress recovery, controlled replacement, completion, or a
  controlled blocked state.

#### Scenario: Legacy timeout branch fails
- **WHEN** the process liveness model evaluates a state that uses
  `timeout_unknown`, host-liveness timeout, or bounded wait timeout as a current
  replacement authority
- **THEN** the state is rejected by an explicit invariant.
