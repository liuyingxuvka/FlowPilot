## ADDED Requirements

### Requirement: Multi-Layer Field Contract Mesh

FlowPilot SHALL maintain a FlowGuard-backed field contract mesh with a parent
critical-field model and child field families that cover every observed field in
current source, test, simulation, template, and current spec surfaces.

#### Scenario: all observed fields are classified

- **WHEN** the field mesh check runs
- **THEN** every observed field is assigned to exactly one child field family
- **AND** every observed field is assigned to an importance tier
- **AND** the check fails if any observed field is unclassified.

#### Scenario: critical fields bind to code

- **WHEN** a field is listed in the parent critical-field model
- **THEN** the field mesh check verifies that the field is observed in source
- **AND** its current validator is present
- **AND** the check fails when a critical field is unbound.

#### Scenario: old field paths cannot be current production paths

- **WHEN** old FlowPilot field names, fixed-role startup gates, or old boot
  actions appear in production or prompt surfaces
- **THEN** the field mesh check fails
- **AND** such names may appear only in negative tests or historical evidence.

### Requirement: Split Entrypoint Install And Handoff Binding

FlowPilot SHALL keep `flowpilot_new.py` as the public command entrypoint after
splitting the implementation into child modules.

#### Scenario: role handoff uses the public entrypoint

- **WHEN** a role handoff is rendered
- **THEN** every command in the handoff uses `flowpilot_new.py`
- **AND** no handoff command names internal split modules.

#### Scenario: install checks cover split entry modules

- **WHEN** install checks verify required repository files
- **THEN** they require `flowpilot_new.py`, `flowpilot_new_cli.py`,
  `flowpilot_new_role_commands.py`, `flowpilot_new_run_commands.py`, and
  `flowpilot_new_shared.py`.
