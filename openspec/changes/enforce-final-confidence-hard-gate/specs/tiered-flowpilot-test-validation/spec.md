## ADDED Requirements

### Requirement: Test tiers expose final confidence gate explicitly
FlowPilot test tiers SHALL expose a named final-confidence validation command so broad completion claims can consume the final evidence boundary instead of inferring it from focused subchecks.

#### Scenario: Final confidence tier is discoverable
- **WHEN** an agent lists test tiers
- **THEN** `final-confidence` SHALL appear as a named tier
- **AND** the tier SHALL run the final confidence hard gate

#### Scenario: Routine tier does not silently imply final confidence
- **WHEN** a routine tier passes without the final confidence gate
- **THEN** the result SHALL NOT imply broad final confidence
- **AND** final confidence SHALL remain pending until the named final-confidence tier or equivalent gate evidence is consumed
