## ADDED Requirements

### Requirement: Fake rehearsal covers lifecycle interruption and recovery
FlowPilot SHALL include fake AI rehearsal coverage for the new runtime
lifecycle guard, including interruption, manual resume, missing ACK, ACK-only
wait, inactive lease, stale result, repeated next action, and terminal stop
authorization.

#### Scenario: Fake rehearsal proves nonterminal resume
- **WHEN** a fake AI rehearsal pauses or resumes a run before final closure
- **THEN** the rehearsal MUST prove the lifecycle guard reloads current-run
  ledger state
- **AND** the resumed run MUST continue to the next legal packet, wait, or
  recovery state without claiming terminal completion.

#### Scenario: Fake rehearsal catches bad terminal stop
- **WHEN** a fake AI rehearsal attempts to treat a nonterminal next action as
  completion
- **THEN** the rehearsal MUST reject the row or record it as a known-bad hazard
- **AND** the row MUST NOT count as terminal FlowPilot confidence.

#### Scenario: Fake rehearsal separates fake confidence from live confidence
- **WHEN** lifecycle guard coverage is produced by deterministic fake agents
- **THEN** the evidence MUST identify the confidence as fake/scoped rehearsal
- **AND** it MUST NOT claim live background-agent reliability.
