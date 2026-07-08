## ADDED Requirements

### Requirement: Coverage matrix includes stale submit and duplicate dispatch bad cases

FlowPilot SHALL include D-card or equivalent synthetic coverage rows for stale
result submissions, already-accepted duplicate submissions, noncurrent packet
submissions, inactive lease submissions, repeated dispatch, and stale
historical result authority.

#### Scenario: Stale submit coverage row is missing
- **WHEN** the synthetic coverage matrix is generated
- **THEN** it MUST include a row proving stale or noncurrent result submission
  cannot allocate a result id or append `packet.result_ids`
- **AND** missing ownership for that row MUST fail the coverage gate

#### Scenario: Repeated dispatch row is missing
- **WHEN** the synthetic coverage matrix is generated
- **THEN** it MUST include a row proving repeated dispatch-current-role returns
  or preserves the existing active lease rather than creating a second active
  lease

### Requirement: Reviewer mechanical-boundary bad cases are covered

FlowPilot SHALL include coverage rows that distinguish mechanical Reviewer
runtime failures from semantic Reviewer quality obligations.

#### Scenario: Reviewer mechanical bad case is missing
- **WHEN** the coverage matrix is generated
- **THEN** it MUST include rows for missing current result-body open receipt,
  stale review subject, missing evidence path, empty required field, and
  forbidden-field Reviewer results
- **AND** those rows MUST be owned by runtime or fake-AI replay evidence

#### Scenario: Reviewer semantic boundary is overclaimed
- **WHEN** coverage describes shallow Reviewer prose behavior
- **THEN** the coverage boundary MUST state whether the evidence proves
  mechanical rejection, fake-AI modeled weakness, or prompt/model obligation
- **AND** it MUST NOT claim runtime semantic grading.
