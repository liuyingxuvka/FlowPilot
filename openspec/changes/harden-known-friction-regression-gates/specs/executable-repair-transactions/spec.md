## ADDED Requirements

### Requirement: PM repair commit exposes only post-decision executable waits
FlowPilot SHALL commit PM control-blocker repair decisions so active blocker
allowed events, repair transaction records, indexes, and daemon-visible
run-state flags describe the same post-decision state.

#### Scenario: PM repair decision enables material recheck events
- **WHEN** PM submits a valid `packet_reissue` repair decision that records
  material recheck events requiring `pm_control_blocker_repair_decision_recorded`
- **THEN** Router MUST persist the PM decision flag before those events are
  exposed as active blocker waits or daemon-computed next actions.

#### Scenario: Half-committed repair state is detected
- **WHEN** active blocker records contain allowed events whose required flags
  are not satisfied in the current daemon-visible run state
- **THEN** Router MUST treat the projection as invalid and repair or block it
  without claiming the wait is executable.

### Requirement: Packet reissue continues material repair work
FlowPilot SHALL continue material repair work after a valid `packet_reissue`
instead of projecting a stale pre-decision wait for PM repair.

#### Scenario: Packet reissue registers fresh producer
- **WHEN** PM commits a valid `packet_reissue` repair transaction with a fresh
  material repair generation
- **THEN** Router MUST expose a next action that either relays or waits on the
  fresh producer evidence for that generation, not an unresolved PM decision.

#### Scenario: Packet reissue producer is missing
- **WHEN** a committed `packet_reissue` lacks the packet, batch, generation, or
  producer evidence required to continue
- **THEN** Router MUST keep or create a control blocker that names the missing
  producer evidence instead of advertising a non-executable wait.
