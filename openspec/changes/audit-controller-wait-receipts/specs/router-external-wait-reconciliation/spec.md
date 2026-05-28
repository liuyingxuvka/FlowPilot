## ADDED Requirements

### Requirement: External waits distinguish missing return from stale control plane
Router-facing wait projections SHALL distinguish no formal return from formal
return evidence that has not been reconciled into the expected Controller
action, event release, or next-action notice.

#### Scenario: Formal return absent
- **WHEN** an external wait is active
- **AND** no matching formal return surface exists
- **THEN** the wait projection remains ordinary waiting.

#### Scenario: Formal return exists but reconciliation is stale
- **WHEN** an external wait is active
- **AND** matching formal return evidence exists
- **AND** the wait remains active with no expected release, Controller action, or next-action notice
- **THEN** the wait projection includes a stale control-plane classification.

#### Scenario: Formal return already reconciled
- **WHEN** matching formal return evidence exists
- **AND** Router has exposed the matching release, event, Controller action, or next-action notice
- **THEN** the wait projection does not report the role as still needing to submit the same return.
