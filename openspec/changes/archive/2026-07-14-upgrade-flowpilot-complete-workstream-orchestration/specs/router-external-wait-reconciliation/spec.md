## MODIFIED Requirements

### Requirement: Repair follow-up waits carry producer evidence
Router SHALL expose a post-repair `await_role_decision` row only when the awaited external event has validated producer evidence.

#### Scenario: Follow-up wait records producer evidence
- **WHEN** Router commits a repair transaction that legitimately waits for a follow-up external event
- **THEN** the exposed wait row MUST include the allowed external events and the producer evidence source, such as a current ordinary work packet/result identity, queued Controller action, existing event producer, or bounded repair work packet.

#### Scenario: Empty follow-up wait becomes PM correction
- **WHEN** a committed repair transaction would otherwise expose a follow-up wait with no producer evidence
- **THEN** Router MUST refuse to expose that wait
- **AND** Router MUST require PM to submit a corrected executable repair decision or a supported blocker/terminal outcome.

#### Scenario: Producer evidence is current-packet scoped
- **WHEN** the awaited event is an ordinary research or PM role-work result after repair
- **THEN** Router MUST bind producer evidence to the current run, packet, lease, and required result contract
- **AND** Router MUST NOT accept superseded results, stale global flags, or a retired material generation as producer evidence.

## REMOVED Requirements

### Requirement: PM material disposition closes waits only for the current generation
**Reason**: The material-scan packet family and its PM disposition event are retired; retaining a generation-specific success rule would keep that obsolete route executable.

**Migration**: Current research, PM role-work, and current-node waits close only through their existing current packet/result identity and PM disposition contracts. Retired material disposition events are mechanically rejected and cannot close a wait.
