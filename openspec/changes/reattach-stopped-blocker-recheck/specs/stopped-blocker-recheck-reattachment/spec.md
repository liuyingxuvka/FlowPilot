## ADDED Requirements

### Requirement: User-authorized stopped blockers can reattach to required recheck
FlowPilot SHALL expose a current-runtime stopped-blocker recovery resolution
that, after explicit user request, moves a PM-stopped semantic blocker back to
its required FlowGuard or Reviewer recheck path without clearing the blocker.

#### Scenario: Controller repaired a stopped evidence path
- **WHEN** a semantic blocker is `stopped` because PM chose `stop_for_user`
  and the user explicitly requests recovery after Controller or user repair
- **THEN** FlowPilot records the recovery intent, marks the blocker
  `awaiting_recheck`, and issues a fresh required recheck packet.

#### Scenario: Reattachment without user request is rejected
- **WHEN** Controller calls the stopped-blocker recheck recovery without
  explicit user request
- **THEN** FlowPilot rejects the command and keeps the blocker stopped.

#### Scenario: Reattachment does not clear the blocker
- **WHEN** FlowPilot reattaches a stopped blocker to its required recheck path
- **THEN** FlowPilot MUST NOT mark the blocker `cleared`, close the target
  packet, or treat break-glass evidence as route-gate acceptance.

#### Scenario: Owner pass clears through existing gate logic
- **WHEN** the fresh required recheck packet returns a passing owner result
- **THEN** FlowPilot clears the blocker through the existing semantic blocker
  pass-clearing logic.

### Requirement: PM-stopped packet status is restorable
FlowPilot SHALL preserve enough target-packet status to resume routing after
PM `stop_for_user` without adding a parallel recovery ledger.

#### Scenario: Stop records previous target status
- **WHEN** PM applies `stop_for_user` to a semantic blocker target packet
- **THEN** FlowPilot records the target packet's previous status before
  setting it to `pm_stopped`.

#### Scenario: Recovery restores the stopped target
- **WHEN** FlowPilot reattaches the stopped blocker to required recheck
- **THEN** FlowPilot restores the target packet to the recorded previous status
  before issuing fresh recheck work.
