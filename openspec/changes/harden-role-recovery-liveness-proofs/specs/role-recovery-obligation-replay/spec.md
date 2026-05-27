## ADDED Requirements

### Requirement: Recovered-role obligation replay starts after liveness proof
Router SHALL scan and replay recovered-role obligations only after current
transaction recovery readiness and host liveness proof have both passed.

#### Scenario: Recovery report does not match latest transaction
- **WHEN** a recovered role has outstanding obligations
- **AND** the recovery report is older than the latest role recovery
  transaction
- **THEN** Router MUST NOT settle or reissue those obligations from the stale
  report.

#### Scenario: Current recovery is not addressable
- **WHEN** a recovered role has outstanding obligations
- **AND** current host liveness proof is missing for that role
- **THEN** Router MUST keep role recovery ahead of obligation replay.
