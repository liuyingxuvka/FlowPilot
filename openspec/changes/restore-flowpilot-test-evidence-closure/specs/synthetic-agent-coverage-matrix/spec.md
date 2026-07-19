## ADDED Requirements

### Requirement: Forbidden surfaces have non-vacuous end-to-end coverage
The synthetic agent matrix SHALL account every current forbidden field and
forbidden alias from registration through handoff projection, case generation,
execution, and proof receipt.

#### Scenario: Forbidden registry is non-empty
- **WHEN** base packet-result families declare forbidden fields
- **THEN** registered, projected, generated, selected, executed, and passed
  counts MUST be reported
- **AND** a zero projected/generated/executed count MUST fail rather than pass
  an empty loop

#### Scenario: A forbidden field is submitted
- **WHEN** the fake AI adds one registered forbidden path to an otherwise legal
  checklist-derived payload
- **THEN** public submit-result MUST reject it with the expected oracle
- **AND** protected packet, route, result, and side-effect state MUST remain
  unchanged

### Requirement: Coverage reports distinguish model ownership from execution
Synthetic coverage reports SHALL NOT use owned model-cell counts, test-name
presence, or abstract expected metadata as executed test evidence.

#### Scenario: One test name is reused for many model cells
- **WHEN** a model maps multiple cells to one test target
- **THEN** the report MUST show the mapping as planned/reused coverage
- **AND** executed/passed counts MUST come only from a current proof artifact

### Requirement: Current-authority and compact-review coverage is non-vacuous
The synthetic matrix SHALL register structured authority-reference mutations,
requested-role target-set mutations, workstream semantic hazards, compact
Reviewer fields, and deleted Reviewer fields as distinct current-contract
coverage classes.

#### Scenario: Structured authority reference is mutated
- **WHEN** a case removes or changes the reference kind, authority id, owner,
  path, fingerprint, consumer scope, or applicable runtime identity
- **THEN** the current public path MUST produce the declared block or repair
  oracle
- **AND** the matrix MUST NOT replace the reference with prose, history, or a
  newest-artifact fallback

#### Scenario: Compact Reviewer result is generated
- **WHEN** fake AI generates a positive review result
- **THEN** it MUST use only the compact current fields and consume the delivered
  stage policy plus current workstream/evidence context
- **AND** `independent_challenge` and other retired broad fields MUST appear
  only in non-zero forbidden/deleted negative coverage

#### Scenario: Workstream rows exist without semantic support
- **WHEN** the result contains the required workstream subsection but actual
  artifacts, delegation integration, verification, unresolved items, or claim
  consistency do not support completion
- **THEN** the Reviewer-semantic oracle MUST remain negative
- **AND** mechanical field presence MUST NOT be counted as semantic pass
