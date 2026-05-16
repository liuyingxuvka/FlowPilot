## ADDED Requirements

### Requirement: Officer modeling work uses PM request packets

FlowPilot SHALL route Process and Product FlowGuard officer modeling work
through PM-authored request packets or registered PM role-work requests before
accepting officer report output.

#### Scenario: PM requests officer modeling
- **WHEN** the PM needs Process or Product FlowGuard officer modeling evidence
- **THEN** the current run records a packet-backed officer request with target
  role, requested model boundary, expected report contract, and current route or
  gate context.

#### Scenario: Officer report without request is rejected
- **WHEN** an officer report arrives without a matching current-run PM request
  packet or registered PM role-work request
- **THEN** the Router treats the output as unauthorized and does not advance the
  gate.

### Requirement: Officer reports use router-authorized events

FlowPilot SHALL accept officer report completion only through router-authorized
packet/result or role-output events for the current wait state.

#### Scenario: Invented direct officer event is blocked
- **WHEN** an officer submits a report event name that is not present in the
  current Router allowed external events or packet-result contract
- **THEN** the Router records a protocol blocker or repair need instead of
  treating the report as complete.

#### Scenario: Authorized officer result completes request
- **WHEN** an officer result envelope matches the request packet, report
  contract, role identity, and current wait state
- **THEN** the Router may mark that officer request complete and relay the
  report to the PM for disposition.

### Requirement: Officer report bodies remain sealed from Controller

FlowPilot SHALL keep officer report bodies sealed from Controller relay paths.

#### Scenario: Controller sees envelope only
- **WHEN** an officer report is relayed through the Controller
- **THEN** the Controller-visible data contains envelope metadata, body path,
  hash, role, contract, and status only
- **AND** the Controller does not read or summarize the sealed report body.
