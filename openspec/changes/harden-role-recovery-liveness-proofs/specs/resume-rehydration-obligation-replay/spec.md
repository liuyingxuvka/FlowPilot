## ADDED Requirements

### Requirement: Resume replay waits for proven role liveness
Router SHALL run resume obligation replay only after the recovered or
rehydrated role set has current transaction-scoped host liveness proof.

#### Scenario: Resume role has stale recovery evidence
- **WHEN** resume rehydration finds a role recovery report that does not match
  the latest recovery transaction
- **THEN** Router MUST NOT deliver PM resume decision or replay obligations for
  that role
- **AND** Router MUST surface current role recovery before downstream resume
  work.

#### Scenario: Resume role has agent id without addressability
- **WHEN** resume rehydration finds a role slot with an agent id but no current
  host addressability proof
- **THEN** Router MUST treat the role as not ready for resume replay.
