## ADDED Requirements

### Requirement: Break-glass patches require validation disposition
FlowPilot SHALL close break-glass patch records through the existing break-glass lifecycle after validation evidence is available.

#### Scenario: Patch validation finalizes disposition
- **WHEN** a break-glass patch record has validation evidence that has been run or superseded by a permanent FlowPilot fix
- **THEN** the patch MUST record `final_disposition`
- **AND** the related incident MUST either close or name the remaining blocker

#### Scenario: Pending patch blocks clean control-plane claim
- **WHEN** a break-glass patch remains temporary and lacks final disposition after validation is required
- **THEN** FlowGuard and runtime audit MUST continue to report the control plane as not clean.
