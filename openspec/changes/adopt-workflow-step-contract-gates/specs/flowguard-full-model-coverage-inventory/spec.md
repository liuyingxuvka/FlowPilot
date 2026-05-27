## ADDED Requirements

### Requirement: Full diagnostic consumes workflow-step and layered evidence
The full model-test-code diagnostic SHALL include workflow-step contract
surfaces and SHALL classify legacy full commands by current layered parent
proof status before final confidence is evaluated.

#### Scenario: Workflow-step runner appears in diagnostic inventory
- **WHEN** the full diagnostic inventory is generated
- **THEN** the workflow-step contract runner MUST appear as a model-check
  surface
- **AND** matching ordinary tests MUST appear as current evidence.

#### Scenario: Legacy full row is reclassified only after current layered proof
- **WHEN** a legacy-full Meta or Capability command has background evidence
  that is running, failed, stale, or missing
- **AND** the corresponding layered full parent proof is current and valid
- **THEN** the diagnostic MAY classify the legacy-full row as superseded by
  layered full proof
- **AND** it MUST keep the row as stale evidence if the layered proof is not
  current.

### Requirement: Final confidence fails on unresolved diagnostic gaps
FlowPilot SHALL reject final confidence when the full diagnostic has unresolved
non-deferred gaps, stale validation evidence, or actionable structure findings.

#### Scenario: Final confidence passes only with no actionable findings
- **WHEN** the final confidence gate runs
- **THEN** `full_coverage_ok` MUST be true
- **AND** `release_convergence_ok` MUST be true
- **AND** the final confidence result MUST include the diagnostic result path.
