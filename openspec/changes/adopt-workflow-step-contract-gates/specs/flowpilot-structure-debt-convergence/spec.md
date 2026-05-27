## ADDED Requirements

### Requirement: Runtime structure findings are cleared by current split evidence
FlowPilot SHALL clear runtime `needs_structure_split` diagnostic findings only
when the parent module is reduced below the active threshold or the diagnostic
records an explicit StructureMesh-safe skip with current parity evidence.

#### Scenario: Controller break-glass helper is split behind compatibility facade
- **WHEN** controller break-glass helper functions move into child modules
- **THEN** `flowpilot_controller_break_glass.py` MUST continue exporting the
  same public functions
- **AND** existing controller break-glass tests MUST pass
- **AND** the full diagnostic MUST NOT report `needs_structure_split` for the
  controller break-glass parent module.

#### Scenario: Daemon runtime diagnostics move behind compatibility facade
- **WHEN** router daemon runtime diagnostics move into a child module
- **THEN** `flowpilot_router_daemon_runtime.py` MUST continue exporting the
  same public daemon functions
- **AND** daemon runtime/source-contract tests MUST pass
- **AND** the full diagnostic MUST NOT report `needs_structure_split` for the
  daemon runtime parent module.
