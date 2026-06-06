## ADDED Requirements

### Requirement: Deferred Structure Split Findings Are Current

The full model coverage inventory SHALL report deferred structure split
findings from current diagnostics and SHALL remove them only when the current
model-test alignment diagnostics no longer emit the finding.

#### Scenario: Closed split findings disappear from inventory

- **WHEN** the HFF batch has been split and the full inventory is regenerated
- **THEN** `deferred_structure_split_count` SHALL be derived from current
  diagnostics
- **AND** the human report SHALL show `Deferred structure split count: 0` only
  when the machine-readable diagnostics have no remaining
  `needs_structure_split` findings.

#### Scenario: Live-run evidence remains separately scoped

- **WHEN** no `.flowpilot/current.json` exists during final confidence
  validation
- **THEN** the inventory and final report SHALL keep live-run evidence scoped
  or blocked
- **AND** they SHALL NOT treat historical run artifacts, newest-run lookup, or
  repo-root fallback as current-run completion evidence.
