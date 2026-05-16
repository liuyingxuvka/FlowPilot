## ADDED Requirements

### Requirement: Startup metadata is available before activation
The system SHALL make startup authorization metadata available before PM startup
activation without exposing the full user task body to PM.

#### Scenario: PM reviews startup metadata
- **WHEN** FlowPilot is in startup intake or startup fact review before startup activation
- **THEN** PM-visible context SHALL include startup answers, run identity, current-run pointers, role evidence, continuation evidence, display evidence, and body hashes or paths only

#### Scenario: Controller remains body-blind
- **WHEN** startup metadata is prepared or delivered
- **THEN** Controller SHALL NOT read, summarize, execute, or rewrite the full user task body

### Requirement: Full user intake waits for startup activation
The system SHALL keep the full `user_intake` packet sealed from PM until PM
startup activation has been approved.

#### Scenario: Startup activation is not approved
- **WHEN** `startup_activation_approved` is false
- **THEN** `user_intake_delivered_to_pm` SHALL remain false and the packet ledger SHALL NOT record a PM delivery for the full `user_intake` body

#### Scenario: Startup activation is approved
- **WHEN** PM records a valid startup activation approval
- **THEN** the Router SHALL expose the full `user_intake` packet as the first post-startup PM intake mail item
- **AND** Controller SHALL relay the packet envelope before PM may open the full body
- **AND** the packet ledger SHALL record a Controller relay signature for `user_intake`

#### Scenario: Release finalizer is retried
- **WHEN** the Router startup settlement finalizer runs more than once before or after startup activation approval
- **THEN** it SHALL NOT create Router-only PM open authority for `user_intake`
- **AND** it SHALL leave PM delivery to the standard Controller `deliver_mail` path

### Requirement: Formal post-startup work waits for full PM user intake
The system SHALL require the PM full user intake packet to be available before
material scan, product architecture, route drafting, or implementation work can
start.

#### Scenario: Material scan entry is requested
- **WHEN** Router is ready to enter material scan
- **THEN** it SHALL confirm startup activation approval, Controller relay, and PM delivery of the full `user_intake` packet before delivering material scan work
