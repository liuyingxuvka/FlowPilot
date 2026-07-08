## ADDED Requirements

### Requirement: Parent Release Confidence Rejects Stale Layered Proof
FlowPilot parent Meta and Capability model evidence SHALL distinguish routine
thin-parent confidence from release confidence when layered full proof input
fingerprints are stale.

#### Scenario: Layered proof fingerprint is stale
- **WHEN** a parent check reports `release_confidence=requires_full_regression` or a layered full proof reason such as `input fingerprint changed`
- **THEN** FlowPilot SHALL treat release confidence as pending until the full proof is rerun and current
- **AND** it SHALL NOT use the routine thin-parent pass as release proof.

#### Scenario: Full proof is refreshed
- **WHEN** a layered full parent proof is rerun for release confidence
- **THEN** the proof artifact SHALL record current result and input fingerprints for the model version used by the final claim.
