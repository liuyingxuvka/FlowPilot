## MODIFIED Requirements

### Requirement: Recipient busy checks use true unresolved ownership

The dispatch recipient gate SHALL classify a target role as busy only from unresolved work that the role can actually act on.

#### Scenario: Superseded unrelayed request does not block replacement
- **WHEN** an old PM role-work request is still Controller-held and was not relayed to the target role
- **AND** a new PM role-work request supersedes it
- **THEN** the old request MUST be reconciled to terminal superseded/canceled state
- **AND** the old request MUST NOT block relay of the replacement request as target-role busy

#### Scenario: Truly relayed old work still blocks independent replacement
- **WHEN** the target role has a relayed packet, active holder lease, or unresolved returned-output obligation for an old request
- **AND** that old request is not terminal
- **THEN** Router MUST continue to treat the target role as busy for independent replacement work
