## MODIFIED Requirements

### Requirement: Verified packet open authorizes addressed-role work

FlowPilot SHALL treat a successful current-run `flowpilot_new.py open-packet` command as sufficient authority for the addressed role to work the opened packet inside its role and packet boundary.

#### Scenario: PM opens assigned startup or planning packet

- **WHEN** PM opens an assigned packet with `flowpilot_new.py open-packet` and the runtime verifies current assignment, active lease, ACK, target role, and body hash
- **THEN** the runtime records that the successful open authorizes PM to work the packet
- **AND** PM MUST NOT wait for additional body exposure in the ACK response before deciding or returning a formal existing PM output.

#### Scenario: Ordinary role opens assigned work packet

- **WHEN** the addressed worker, reviewer, FlowGuard operator, research worker, or UI QA role opens an assigned packet with the current `flowpilot_new.py open-packet` command and current assignment/hash checks pass
- **THEN** the role has authority to work only that packet
- **AND** the role MUST submit the expected result or an existing formal blocker/PM-suggestion output instead of waiting in chat.

### Requirement: Path-only or prompt-only packet handoff never authorizes packet open

FlowPilot SHALL reject packet open attempts that rely only on Controller chat text, displayed paths, or prompts without a matching current-run lease assignment and ACK.

#### Scenario: Role receives path without current lease

- **WHEN** a role runs `flowpilot_new.py open-packet` and the packet is not assigned to that lease
- **THEN** the runtime MUST reject the open
- **AND** the runtime MUST NOT return sealed body content.

#### Scenario: Role opens after current assignment and ACK

- **WHEN** Router assigned the packet to the lease, the lease is active, ACK is recorded, and the packet body hash still matches the envelope
- **THEN** `flowpilot_new.py open-packet` MUST accept the packet and write the normal sealed-body-open event.
