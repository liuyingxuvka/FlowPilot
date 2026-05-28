## ADDED Requirements

### Requirement: Fixed-router-event outputs require Router-directed submission
FlowPilot SHALL reject local-only role-output submission for any output contract
that declares a fixed Router event, unless the call also records that Router
event through the existing Router-directed submission path.

#### Scenario: Local-only submission is rejected for fixed Router event
- **WHEN** a role submits an output whose contract declares `router_event`
- **AND** the runtime entrypoint is local-only `submit-output`
- **THEN** the runtime MUST reject the submission before reporting Router
  progress
- **AND** the error MUST name `submit-output-to-router` or the equivalent
  Router-directed return path.

#### Scenario: Router-directed submission records event evidence
- **WHEN** a role submits a fixed-router-event output through
  `submit-output-to-router`
- **THEN** the role-output receipt MUST record the local body and receipt
  evidence
- **AND** Router history or event state MUST record the fixed Router event in
  the same successful operation.

### Requirement: Role-output status separates local receipt from Router event
FlowPilot SHALL expose local receipt and Router event milestones separately for
formal role outputs.

#### Scenario: Local receipt without Router event is not consumed
- **WHEN** a role-output body and runtime receipt exist
- **AND** no matching Router event has been recorded
- **THEN** the status projection MUST NOT present the output as consumed by
  Router
- **AND** Controller MUST NOT treat the status as a decision, approval, or wait
  closure.

#### Scenario: Router event confirms consumed output
- **WHEN** a matching Router event has been recorded for the role-output
  envelope
- **THEN** the status projection MAY report the output as Router-consumed
- **AND** it MUST include receipt or event evidence sufficient for later replay.
