## MODIFIED Requirements

### Requirement: Repair dossier obligations bind model, code, and tests
FlowPilot SHALL bind repair dossier behavior to FlowGuard obligations, owner
code contracts, and current executable test evidence before claiming broad
repair confidence.

#### Scenario: Dossier authorization has model-code-test binding
- **WHEN** repair dossier authorization behavior changes
- **THEN** the FlowGuard model obligation, runtime owner code contract, and
  role-scoped authorization tests MUST reference the same behavior.

#### Scenario: Blocker routing has observed and same-class evidence
- **WHEN** fixed blocker next-action routing is changed
- **THEN** tests MUST cover the observed regression and same-class blocker
  families for every supported blocker class in the stage matrix.

#### Scenario: Cartesian cells are explicit evidence targets
- **WHEN** the repair TestMesh generates a coverage cell
- **THEN** the cell id MUST be traceable to a model obligation, owner code
  boundary, and child-suite test evidence or be explicitly scoped out with a
  reason.

#### Scenario: Install sync evidence is separate from source tests
- **WHEN** source validation passes and the installed skill is synced
- **THEN** install audit and install check evidence MUST be current after sync
- **AND** pre-sync source tests MUST NOT be treated as installed-copy proof.
