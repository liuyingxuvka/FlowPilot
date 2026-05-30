## ADDED Requirements

### Requirement: Control-plane duty model misses are known-friction gates
FlowPilot SHALL treat the new-runtime parser/action-folding/status-readonly failure family as known friction requiring both model coverage and ordinary regression evidence.

#### Scenario: Parser and lifecycle split-brain is registered
- **WHEN** a PM repair decision body contains a structured repair decision plus conflicting rationale words
- **THEN** the known-friction gate MUST require evidence that the structured decision controls blocker lifecycle
- **AND** it MUST reject evidence where free-text words override the structured decision.

#### Scenario: Public control surface gap is registered
- **WHEN** fake rehearsal can progress by direct helper calls that the foreground Controller cannot execute
- **THEN** the known-friction gate MUST require a public-surface rehearsal or command-level test
- **AND** a direct helper-only test MUST NOT count as full evidence for that row.

#### Scenario: Status mutation is registered
- **WHEN** repeated status reads can change lifecycle guard history or stuck classification
- **THEN** the known-friction gate MUST require a status-readonly regression
- **AND** patrol or another stateful command must be the only source of that refresh evidence.
