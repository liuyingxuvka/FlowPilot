## MODIFIED Requirements

### Requirement: Dynamic Agent Responsibilities

The new FlowPilot SHALL request dynamic agent leases only for issued work
packets. All backend responsibilities, including PM, FlowGuard operator,
Reviewer, Validator, and Closure officer, SHALL use the same packet lifecycle:
issued packet, lease, ACK, result, ledger side effect, and next packet.

#### Scenario: First PM packet is issued

- **WHEN** the new route has a PM-bound startup packet
- **THEN** the next action MUST request a PM lease for that packet
- **AND** no fixed six-agent startup requirement is allowed.

#### Scenario: PM result requires FlowGuard

- **WHEN** a PM task packet result is submitted and accepted mechanically
- **THEN** the runtime MUST issue a FlowGuard operator work packet
- **AND** the FlowGuard operator MUST be leased through that packet
- **AND** the runtime MUST NOT require a direct side-command FlowGuard actor.

#### Scenario: FlowGuard result requires review

- **WHEN** a FlowGuard operator packet result records passing evidence for the
  subject PM packet
- **THEN** the runtime MUST issue a Reviewer work packet
- **AND** the Reviewer MUST ACK and submit a result through that packet before
  review acceptance is recorded.

#### Scenario: Review result requires validation and closure

- **WHEN** a Reviewer packet result accepts the subject PM result and evidence
- **THEN** the runtime MUST issue a Validation work packet
- **AND** a valid Validation result MUST issue a Closure work packet
- **AND** a valid Closure result MUST attempt final backward closure.

### Requirement: New Entrypoint End-To-End Closure

The new FlowPilot SHALL progress from startup intake to final backward closure
through current-run packets for every backend role. Final closure MUST require
accepted task, FlowGuard, review, validation, and closure packet evidence.

#### Scenario: Rehearsal end-to-end run

- **WHEN** a deterministic fake-host rehearsal supplies valid results for PM,
  FlowGuard, Reviewer, Validation, and Closure packets
- **THEN** final closure MUST complete
- **AND** the public status MUST still hide sealed bodies
- **AND** no active lease row may remain for a completed packet.

#### Scenario: Black-box fake project rehearsal

- **WHEN** a deterministic fake project is run through the real public CLI from
  startup intake through `status`, `lease-agent`, `ack`, and `submit-result`
- **THEN** the rehearsal MUST reach terminal closure through PM, FlowGuard
  operator, Reviewer, Validator, and Closure officer packets
- **AND** the rehearsal MUST NOT use the internal fake end-to-end helper as its
  proof
- **AND** startup text and fake AI result bodies MUST remain hidden from public
  status.

#### Scenario: Black-box error-flow rehearsal

- **WHEN** black-box rehearsal attempts wrong-role lease, missing-ACK result,
  ACK-only completion, and retired side-command completion
- **THEN** wrong-role lease and retired side commands MUST be rejected
- **AND** missing-ACK and ACK-only paths MUST NOT reach terminal closure
- **AND** a corrected wrong-role scenario MUST recover through the normal
  packet chain to terminal closure.

#### Scenario: Direct side-command completion is attempted

- **WHEN** a caller tries to complete FlowGuard, review, validation, or closure
  without the matching issued packet lifecycle
- **THEN** the formal runtime MUST reject or omit that path from the formal
  public command surface
- **AND** closure MUST remain unproved without packet-backed evidence.
