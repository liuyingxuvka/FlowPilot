## ADDED Requirements

### Requirement: Structural maintenance preserves behavior contracts

Internal refactors MUST preserve public entrypoints, event names, persisted JSON
shapes, protocol semantics, and validation meaning unless a separate
behavior-changing OpenSpec explicitly authorizes the change.

#### Scenario: Router entrypoint remains compatible

- **GIVEN** runtime code is moved from `flowpilot_router.py` into helper modules
- **WHEN** existing callers import and call the original router entrypoints
- **THEN** the calls MUST continue to work with the same inputs, outputs, and
  persisted side effects.

#### Scenario: No protocol shape changes in structure-only refactor

- **GIVEN** event, action, packet, route, or ledger code is extracted
- **WHEN** tests inspect persisted payloads or command output
- **THEN** the JSON field names, event names, status values, and schema markers
  MUST remain unchanged.

### Requirement: Each slice is independently revertible

Each refactor slice MUST move one boundary at a time, preserve a rollback
point, run focused validation, and avoid mixing unrelated cleanup.

#### Scenario: Validation gates next slice

- **GIVEN** a slice changes runtime, model, test, or tooling structure
- **WHEN** the slice is complete
- **THEN** the relevant focused checks MUST pass before starting the next
  boundary.

#### Scenario: Baseline evidence exists

- **GIVEN** the maintenance branch starts
- **WHEN** implementation begins
- **THEN** the baseline commit, version, structure audit, rollback strategy, and
  required validation commands MUST be recorded.

### Requirement: FlowGuard models the refactor process risk

The maintenance pass MUST include a focused FlowGuard model that rejects known
bad refactor-process states before production code movement is trusted.

#### Scenario: Known bad process paths fail

- **GIVEN** a refactor skips baseline, deletes compatibility entrypoints,
  changes protocol fields, validates after multiple slices, or pushes before
  install/public-boundary checks
- **WHEN** the structural-refactor model evaluates the state
- **THEN** the model MUST report invariant failures for those hazards.
