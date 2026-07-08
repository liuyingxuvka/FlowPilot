## ADDED Requirements

### Requirement: Projection failures do not replay business submissions

FlowPilot SHALL keep canonical business-result submission separate from
projection/materialization writes. A projection failure MUST surface as a
projection/runtime persistence error and MUST NOT cause stale or duplicate
result submission.

#### Scenario: Materialization fails after ledger save
- **WHEN** a valid current result has been saved to the canonical ledger
- **AND** materialized packet, result, lease, review, evidence, or status files
  fail to write
- **THEN** Runtime MUST report projection failure with the affected path
- **AND** Runtime MUST NOT retry by resubmitting the same business result
- **AND** stale backend result submission remains rejected by the submit ingress

### Requirement: Projection writes are atomic enough for readers

FlowPilot SHALL write materialized JSON/text projections through a complete
write-and-replace strategy so readers do not consume partial projection files.

#### Scenario: Reader observes projection during refresh
- **WHEN** Runtime refreshes materialized run artifacts
- **THEN** a reader MUST see either the previous complete projection or the new
  complete projection
- **AND** partial JSON/text fragments MUST NOT be treated as current evidence.
