## ADDED Requirements

### Requirement: Fake AI rehearsals include contract-misread packages
FlowPilot SHALL maintain deterministic fake-AI rehearsal modes that submit realistic contract-misread packages for AI-facing packet-result contracts.

#### Scenario: Near-synonym fields are rejected and corrected
- **WHEN** a fake-AI rehearsal submits near-synonym fields instead of the exact conditional contract fields
- **THEN** runtime MUST reject or reissue the result without accepting the synonym fields
- **AND** the rehearsal MUST include a corrected retry using the exact current field names from the reissue contract.

#### Scenario: Wrong value type is rejected and corrected
- **WHEN** a fake-AI rehearsal submits a wrong value type for a finite conditional field, such as an object where the contract requires literal `true`
- **THEN** runtime MUST identify the field as not satisfying the contract
- **AND** the corrected retry MUST use the expected literal value and continue on the legal path.

#### Scenario: Missing consumed ids are rejected and corrected
- **WHEN** a fake-AI rehearsal omits required consumed authorized result read ids or repair obligation ids
- **THEN** runtime MUST identify the missing consumed-id field
- **AND** the corrected retry MUST list exactly the current required ids before the result can count as accepted.

#### Scenario: Mechanical responder refuses unreachable conditional branches
- **WHEN** a packet-result contract declares a conditional required field or finite option but the AI-facing contract does not expose a reachable minimal or branch-valid shape for that field
- **THEN** the contract-driven fake-AI responder MUST report a projection finding instead of guessing a payload
- **AND** the corresponding coverage runner MUST keep the contract-exhaustion result non-green until the current contract projection gives the responder enough branch-local information to generate the bad and corrected payload rows.

### Requirement: Fake AI recovery rows preserve GlassBreak boundaries
FlowPilot SHALL keep ordinary fake-AI recovery rows separate from dedicated GlassBreak threshold rows.

#### Scenario: Ordinary retry rows do not reach GlassBreak
- **WHEN** a fake-AI rehearsal injects one recoverable conditional contract mistake and then submits a corrected retry
- **THEN** the rehearsal MUST prove the route returns to the ordinary legal path without triggering GlassBreak.

#### Scenario: Fuse threshold remains covered by dedicated rows
- **WHEN** a dedicated GlassBreak rehearsal repeats the same current-contract failure through the configured threshold
- **THEN** the rehearsal MUST prove the fifth same-class repeat escalates through the GlassBreak path.
