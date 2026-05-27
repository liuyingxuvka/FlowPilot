## MODIFIED Requirements

### Requirement: Router facade remains public compatibility owner
The FlowPilot router split SHALL keep `skills/flowpilot/assets/flowpilot_router.py`
as the stable public import and CLI facade while moving owned implementation
regions into child modules.

#### Scenario: Additional facade bodies are extracted
- **WHEN** self-interrogation, payload-contract, or system-card delivery helpers
  are moved into child owner modules
- **THEN** existing public imports through `flowpilot_router.py` MUST continue to
  work
- **AND** focused router tests MUST pass without caller changes.

### Requirement: StructureMesh owner names match real files
Router StructureMesh target recommendations SHALL name real owner files for
newly extracted child modules.

#### Scenario: New owner module is declared
- **WHEN** a new router owner is added to the StructureMesh target
- **THEN** its target path MUST exist in `skills/flowpilot/assets`
- **AND** the owner MUST declare behavior contracts and validation boundaries.

### Requirement: System-card delivery remains behavior-preserving
System-card and bundle delivery helpers moved out of the facade SHALL preserve
the same action selection, artifact commit, ACK token, and return reconciliation
semantics.

#### Scenario: System-card owner is extracted
- **WHEN** router card and ACK-return tests run
- **THEN** card delivery, bundle delivery, direct ACK, and pending return behavior
  MUST remain compatible.

### Requirement: Local completion includes install and evidence
FlowPilot maintenance SHALL finish with local install synchronization, local
repository validation, and local Git versioning. Remote publication remains
deferred.

#### Scenario: Local maintenance pass is complete
- **WHEN** the extraction and validation pass complete
- **THEN** the installed local FlowPilot skill MUST be source-fresh
- **AND** the work MUST be committed locally
- **AND** no GitHub push, tag, or remote release publication SHALL occur.
