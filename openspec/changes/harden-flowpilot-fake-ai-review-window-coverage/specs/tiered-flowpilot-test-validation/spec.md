## ADDED Requirements

### Requirement: Hardening completion requires focused and model evidence
FlowPilot SHALL NOT claim this hardening complete until focused tests,
FlowGuard matrix checks, topology checks, and install-sync checks that cover
the changed surfaces have current passing evidence.

#### Scenario: Focused tests cover changed behavior
- **WHEN** this change modifies fake AI responder behavior, result contracts, reviewer metadata, blocker repair, or break-glass behavior
- **THEN** the validation set MUST include focused tests for each changed surface
- **AND** broad confidence MUST remain pending if any focused test is missing or stale.

#### Scenario: Matrix and install evidence are refreshed
- **WHEN** contract-exhaustion, current-contract Cartesian, topology, or local install surfaces change
- **THEN** the owning model/result artifacts, topology build/check, install sync audit, and install self-check MUST be refreshed before completion is claimed.
