## ADDED Requirements

### Requirement: Blocking Decisions Use Shared Closure Classification
FlowPilot SHALL use shared closure classification before lifecycle records affect blocker, wait, busy, current-work, scheduler, ACK-return, or PM-role progress decisions.

#### Scenario: Closed obligation clears through canonical classification
- **WHEN** a lifecycle row has evidence that the same obligation identity is closed or terminally settled
- **THEN** the progress scan SHALL treat the row as nonblocking through the shared closure classifier

#### Scenario: Unknown obligation remains visible
- **WHEN** a lifecycle row has an unknown status, missing evidence, or mismatched reconciliation identity
- **THEN** the progress scan SHALL keep the row visible as blocking, repair-required, or needing recheck

### Requirement: Registry Authorities Derive Compatibility Views
FlowPilot SHALL keep control transaction, route action, output-contract, and prompt-policy registries as the authority for their derived runtime views.

#### Scenario: Facade export matches owner-derived view
- **WHEN** public compatibility exports expose control transaction or route action policy maps
- **THEN** those exports SHALL match the values derived or owned by the registry owner module

#### Scenario: Registry drift is detected
- **WHEN** a registry row is added, removed, or renamed without a matching derived view
- **THEN** focused validation SHALL fail before release or installed-skill synchronization

### Requirement: Derived Views Preserve Physical Ledger Boundaries
FlowPilot SHALL NOT merge Controller actions, scheduler rows, packet lifecycle records, return events, role-output envelopes, or terminal records into a single physical table as part of derived-view folding.

#### Scenario: Closure helper reads separate authorities
- **WHEN** a caller needs to know whether progress is blocked
- **THEN** it SHALL read the relevant authority records and ask the shared classifier or derived view without rewriting signed artifacts or collapsing ledger ownership

#### Scenario: Semantic output completion stays separate
- **WHEN** an ACK or receipt record is classified as closed
- **THEN** any required role output, PM decision, reviewer pass, officer report, or semantic package disposition SHALL remain governed by its own contract
