## ADDED Requirements

### Requirement: Final-confidence tier requires terminal-return evidence for exit claims

The `final-confidence` test tier SHALL run the final-confidence hard gate with terminal-return evidence enabled by default. A broad completion or formal Controller-exit claim MUST NOT pass from repository evidence alone.

#### Scenario: Final-confidence tier blocks nonterminal current run

- **WHEN** the `final-confidence` tier is run for a formal FlowPilot exit claim
- **AND** the current run final-preflight reports `controller_stop_allowed=false`
- **THEN** the tier SHALL fail closed
- **AND** the result SHALL include a terminal-return evidence row with the blocking codes.

#### Scenario: Scoped diagnostic opt-out remains visible

- **WHEN** a caller explicitly runs the final-confidence gate in repository-only diagnostic mode
- **THEN** the result SHALL mark terminal-return evidence as scoped out
- **AND** the result SHALL NOT support a claim that FlowPilot may exit.

#### Scenario: Coverage sweep remains a repository diagnostic

- **WHEN** the read-only FlowGuard coverage sweep executes the final-confidence runner
- **THEN** it SHALL use repository-only diagnostic mode
- **AND** the dedicated `final-confidence` tier SHALL remain the strict path for formal FlowPilot exit authority.
