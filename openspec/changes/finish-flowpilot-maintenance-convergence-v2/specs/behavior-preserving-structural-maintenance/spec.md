## MODIFIED Requirements

### Requirement: Structural maintenance preserves behavior contracts

Internal refactors MUST preserve public entrypoints, event names, persisted JSON
shapes, protocol semantics, validation meaning, and v2 convergence evidence
ownership unless a separate behavior-changing OpenSpec explicitly authorizes
the change.

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

#### Scenario: V2 convergence evidence remains attached

- **GIVEN** a structure split moves code that is referenced by a v2 residual
  FlowGuard group
- **WHEN** the split is completed
- **THEN** the residual group's model/test/code evidence SHALL be refreshed or
  explicitly marked stale
- **AND** final convergence SHALL NOT consume stale pre-split evidence as a
  pass.
