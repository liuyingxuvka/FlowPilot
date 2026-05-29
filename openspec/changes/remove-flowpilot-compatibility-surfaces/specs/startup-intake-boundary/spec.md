## ADDED Requirements

### Requirement: Startup Intake Rejects Legacy Chat Payloads
FlowPilot startup intake SHALL require the current startup intake envelope and
SHALL reject legacy chat-body payload paths.

#### Scenario: Current startup intake envelope is supplied
- **WHEN** startup input arrives through the current startup intake envelope
- **THEN** FlowPilot records the startup answers through current run-scoped
  startup state

#### Scenario: Legacy chat payload is supplied
- **WHEN** startup input arrives through legacy `payload.user_request.text` or
  legacy startup-answer compatibility records
- **THEN** FlowPilot rejects that input as unsupported
- **AND** FlowPilot SHALL NOT canonicalize the legacy payload into current
  startup answers
