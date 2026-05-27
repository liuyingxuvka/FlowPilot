## ADDED Requirements

### Requirement: Repair follow-up waits carry producer evidence
Router SHALL expose a post-repair `await_role_decision` row only when the awaited external event has validated producer evidence.

#### Scenario: Follow-up wait records producer evidence
- **WHEN** Router commits a repair transaction that legitimately waits for a follow-up external event
- **THEN** the exposed wait row MUST include the allowed external events and the producer evidence source, such as current packet generation, queued Controller action, existing event producer, or bounded repair work packet.

#### Scenario: Empty follow-up wait becomes PM correction
- **WHEN** a committed repair transaction would otherwise expose a follow-up wait with no producer evidence
- **THEN** Router MUST refuse to expose that wait
- **AND** Router MUST require PM to submit a corrected executable repair decision or a supported blocker/terminal outcome.

#### Scenario: Producer evidence is generation-scoped
- **WHEN** the awaited event is a material-scan worker result after repair
- **THEN** Router MUST bind producer evidence to the current material packet generation
- **AND** Router MUST NOT accept superseded packet results or stale global flags as producer evidence.
