# flowpilot-control-plane-lifecycle Delta

## ADDED Requirements

### Requirement: Semantic loop detection supplements action-key repetition
FlowPilot SHALL treat same-family repair repetition as a lifecycle hazard even
when new packets, route versions, or ledger events make the action key change.

#### Scenario: New packet ids do not hide a loop
- **WHEN** a repair chain creates new packet ids or route-node ids
- **AND** the normalized family shows the same blocker class and gate repeating
- **THEN** lifecycle control MUST use the same-family attempt count rather than
  treating the new packet id alone as proof of progress.

#### Scenario: Threshold evidence is metadata only
- **WHEN** FlowPilot exposes repair-loop threshold evidence
- **THEN** the evidence includes only controller-visible metadata and does not
  expose sealed packet, result, report, or blocker bodies.
