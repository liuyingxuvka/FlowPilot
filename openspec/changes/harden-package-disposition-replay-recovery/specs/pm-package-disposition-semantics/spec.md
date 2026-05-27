## ADDED Requirements

### Requirement: Repair-owned package conflicts are replay evidence, not fresh dispositions

The Router SHALL keep a same-package different-body PM disposition as a hard
conflict, but when that conflict is already represented by an active control
blocker or PM repair transaction, later replay of the same stale conflicting
evidence SHALL be classified as repair-owned conflict evidence rather than a
fresh ordinary disposition.

#### Scenario: Control blocker owns the conflicting package replay

- **GIVEN** a PM package-result disposition has already been recorded for a
  batch and packet generation
- **AND** a later disposition for the same router event, batch id, packet ids,
  and packet generation id has a different body hash
- **AND** Router has already materialized an active control blocker for that
  package conflict
- **WHEN** the later disposition is replayed from durable role-output storage
- **THEN** Router SHALL NOT accept the later body as a package disposition
- **AND** Router SHALL NOT write a duplicate control blocker or duplicate PM
  package side effect
- **AND** Router SHALL retain the active repair path as the owner of the
  conflict.

#### Scenario: PM repair decision owns the conflicting package replay

- **GIVEN** a same-package different-body conflict has an active PM repair
  decision or repair transaction
- **WHEN** stale role-output evidence for the conflicting body is replayed
- **THEN** Router SHALL classify the replay as repair-decision-owned stale
  conflict evidence
- **AND** Router SHALL preserve the repair transaction's legal follow-up wait
  or PM correction wait.

### Requirement: Same-class package conflict replay coverage is cross-kind

The repair-owned conflict replay rules SHALL apply consistently to material
scan, research result, and current-node result package dispositions.

#### Scenario: Research conflict replay is repair-owned

- **GIVEN** a research result package has a same-generation different-body PM
  disposition conflict
- **AND** a control blocker or PM repair decision owns that conflict
- **WHEN** stale research disposition evidence is replayed
- **THEN** Router SHALL preserve the repair path and SHALL NOT enter daemon
  failure.

#### Scenario: Current-node conflict replay is repair-owned

- **GIVEN** a current-node result package has a same-generation different-body
  PM disposition conflict
- **AND** a control blocker or PM repair decision owns that conflict
- **WHEN** stale current-node disposition evidence is replayed
- **THEN** Router SHALL preserve the repair path and SHALL NOT enter daemon
  failure.
