## ADDED Requirements

### Requirement: Final confidence gate aggregates required evidence
FlowPilot SHALL provide a final confidence hard gate that aggregates required model, test, live-run, defect-family, and risk-ledger evidence into a single decision.

#### Scenario: All required evidence is full and current
- **WHEN** the final confidence gate observes required evidence with passing model checks, passing event-idempotency checks, passing full model-test-code coverage, passing current live-run audit, and full known-friction Risk Evidence Ledger confidence
- **THEN** the gate SHALL report `full_confidence`

#### Scenario: Required evidence is missing
- **WHEN** a required evidence payload is missing
- **THEN** the gate SHALL report `blocked`
- **AND** the report SHALL name the missing evidence source

### Requirement: Current live-run evidence is mandatory
The final confidence hard gate SHALL require a current live-run audit result and SHALL NOT allow skipped live-run evidence to support broad confidence.

#### Scenario: Live audit is skipped
- **WHEN** the control-plane evidence says live-run audit was skipped
- **THEN** the final confidence gate SHALL report `blocked`
- **AND** the report SHALL include `live_run_audit_skipped`

#### Scenario: Live audit reports current findings
- **WHEN** the control-plane evidence has `live_run_audit.ok=false`
- **THEN** the final confidence gate SHALL report `blocked`
- **AND** the report SHALL preserve the live-run finding codes

### Requirement: Full coverage is required for broad confidence
The final confidence hard gate SHALL treat model-test alignment as insufficient for broad confidence unless full model-test-code coverage is also current and complete.

#### Scenario: Alignment passes but full coverage is false
- **WHEN** model-test alignment evidence has `alignment_ok=true`
- **AND** the same evidence has `full_coverage_ok=false`
- **THEN** the final confidence gate SHALL report `blocked`
- **AND** the report SHALL expose the remaining gap codes

### Requirement: Defect-family and risk-ledger proof gates broad confidence
The final confidence hard gate SHALL consume known-friction defect-family gate and Risk Evidence Ledger decisions before broad confidence is reported.

#### Scenario: Known-friction ledger is scoped or blocked
- **WHEN** known-friction evidence has a defect-family gate or Risk Evidence Ledger decision that is not full confidence
- **THEN** the final confidence gate SHALL report `blocked`
- **AND** the report SHALL expose the defect-family or ledger decision

#### Scenario: Known-friction proof is full
- **WHEN** known-friction evidence has full defect-family gate confidence and full Risk Evidence Ledger confidence
- **THEN** the known-friction portion of the final confidence gate SHALL pass

### Requirement: Final confidence report is machine-readable and reviewable
The final confidence hard gate SHALL write a machine-readable JSON report with per-evidence rows, decision, blockers, scoped boundaries, and final summary.

#### Scenario: Gate writes JSON output
- **WHEN** the final confidence gate is run with a JSON output path
- **THEN** the output SHALL include `decision`, `ok`, `evidence_rows`, `blockers`, and `summary`
