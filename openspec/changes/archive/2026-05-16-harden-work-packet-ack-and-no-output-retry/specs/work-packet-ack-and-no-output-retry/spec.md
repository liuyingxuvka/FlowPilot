## ADDED Requirements

### Requirement: Work-item ACKs SHALL continue to formal output

FlowPilot work cards and packet bodies SHALL state that ACK is receipt only and
that any card or packet requiring an output, report, decision, result, or
blocker must continue immediately after ACK and submit through the
Router-directed runtime path.

#### Scenario: Work card ACK does not stop the role

- **WHEN** a role receives a work card that requires a formal output
- **AND** the role submits the card ACK
- **THEN** the card text instructs the role to continue the assigned work
- **AND** the card text states the task is unfinished until Router receives the
  expected output or blocker

#### Scenario: Role identity card still waits for work authority

- **WHEN** a role receives only a role identity card
- **AND** the role submits the card ACK
- **THEN** the card text instructs the role to wait for phase, event, packet,
  lease, or Router-authorized output-contract authority before task work

### Requirement: No-output waits SHALL be reissued before role recovery

Router SHALL treat an ACKed report/result wait with no output and no evidence
of ongoing work as a failed work attempt before treating it as role loss.

#### Scenario: Reachable role produced no output

- **WHEN** Controller reports that the wait target is reachable or completed
  without the expected event
- **AND** the expected Router output is still missing
- **THEN** Router creates a replacement wait for the same authorized work
- **AND** Router marks the original wait `superseded` only after the replacement
  is durable
- **AND** Router does not request role recovery for that first no-output report

#### Scenario: Role unavailable still uses role recovery

- **WHEN** Controller reports that the target role is missing, cancelled,
  unknown, unresponsive, or lost
- **THEN** Router uses the existing role-recovery path
- **AND** Router does not create a same-role no-output reissue as a substitute
  for recovery

#### Scenario: No-output retry budget is exhausted

- **WHEN** the same work wait has already consumed the Router-owned no-output
  retry budget
- **AND** Controller reports no output again
- **THEN** Router records a PM/control-blocker escalation instead of reissuing
  the same task indefinitely
