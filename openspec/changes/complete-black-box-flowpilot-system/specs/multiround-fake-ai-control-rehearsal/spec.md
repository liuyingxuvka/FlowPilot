## ADDED Requirements

### Requirement: Full-System Fake-Agent Rehearsal

Multiround fake-agent rehearsal SHALL exercise the complete FlowPilot runtime
surface, not only the packet protocol foundation.

#### Scenario: Fake agent dies mid-packet

- **WHEN** a fake worker or FlowGuard operator ACKs a packet and then stops
  before result submission
- **THEN** the runtime MUST expire or replace the lease and keep dependent
  route gates incomplete.

#### Scenario: Fake PM mutates route after child evidence

- **WHEN** fake PM route mutation supersedes a node after child evidence exists
- **THEN** the runtime MUST mark affected child evidence stale and require the
  appropriate replay, repair, or rebinding before parent closure.

### Requirement: Fake Rehearsal Does Not Prove Live Host Confidence

Fake-agent rehearsal SHALL produce routine or scoped confidence unless matched
by required live-host evidence.

#### Scenario: Fake chaos matrix passes

- **WHEN** the full fake-agent chaos matrix passes
- **THEN** the completion report MUST still mark live-host confidence as
  unproven until at least the required live-host project run evidence is
  current.
