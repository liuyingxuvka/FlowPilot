# work-packet-ack-and-no-output-retry Spec Delta

## MODIFIED Requirements

### Requirement: Work-item ACKs SHALL continue to formal output
FlowPilot work cards and packet bodies SHALL state that ACK is receipt only,
that output-bearing work must continue after ACK, and that the role must keep
current-run progress metadata fresh while working.

#### Scenario: Work card ACK starts the result wait
- **WHEN** a role ACKs an output-bearing packet
- **THEN** the ACK records receipt and becomes the first liveness evidence for
  the result wait
- **AND** the packet remains unfinished until the expected result or blocker is
  submitted.

#### Scenario: Role progress refreshes liveness only
- **WHEN** a role submits `progress +1` for the assigned active lease and packet
- **THEN** runtime records fresh liveness evidence for the wait
- **AND** progress does not satisfy the final output, review, or quality
  obligation.

#### Scenario: Runtime progress reminder is actionable
- **WHEN** runtime emits a progress reminder for an acknowledged packet
- **THEN** the reminder tells the role to submit the final result if complete,
  immediately write `progress +1` if still working, keep progress frequent
  while continuing, or submit a blocker if unable to continue.

### Requirement: No-output waits SHALL be reissued before role recovery
Router SHALL treat an ACKed report/result wait with no accepted output and no
fresh ACK/progress evidence for 30 minutes as the current replacement condition.
It SHALL NOT require or accept a host-liveness timeout state as a prerequisite.

#### Scenario: Progress after reminder recovers the same lease
- **WHEN** an acknowledged packet has exceeded the progress-reminder threshold
- **AND** the assigned role submits valid progress for the same active lease and
  packet
- **THEN** runtime returns the wait to patrol/grace state
- **AND** no replacement is opened for that packet.

#### Scenario: Unsupported host-liveness no-output branch is absent
- **WHEN** a current wait has no accepted output
- **THEN** runtime chooses wait, remind, or reissue from ACK/progress evidence
  age
- **AND** it does not ask Controller to submit or interpret a
  `timeout_unknown` host-liveness report.
