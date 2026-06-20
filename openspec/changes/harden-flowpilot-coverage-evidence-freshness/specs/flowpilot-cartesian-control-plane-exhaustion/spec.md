## MODIFIED Requirements

### Requirement: Durable Cartesian Evidence Matches Current Matrix
The system SHALL keep the persisted Cartesian control-plane exhaustion result
artifact synchronized with the current model-generated matrix.

#### Scenario: Persisted Cartesian counts match live model counts
- **WHEN** the Cartesian model adds or removes a mutation family, boundary,
  context, consumer, or applicable cell
- **THEN** the persisted result JSON MUST report the same mutation count, full
  product count, applicable count, missing dimensions, missing oracle/feedback
  count, and bridge status as the live runner
- **AND** stale persisted matrix counts MUST fail a regression before a full
  coverage claim is accepted

## ADDED Requirements

### Requirement: Coverage Sweep And Inventory Include Current Runners
The system SHALL keep full coverage sweep and inventory artifacts synchronized
with the repository's current FlowGuard runner set.

#### Scenario: New runner appears in the repository
- **WHEN** a new `simulations/run_*_checks.py` runner exists
- **THEN** the persisted coverage sweep result MUST include that runner
- **AND** the persisted full model coverage inventory MUST include that runner
- **AND** missing fake-AI runtime replay or real-issue backfeed rows MUST fail a
  regression before install/topology evidence can support completion
