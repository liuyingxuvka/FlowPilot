## ADDED Requirements

### Requirement: Prompt Compression Preserves Current Obligations
FlowPilot SHALL preserve the same current role, authority, runtime-return,
fallback, FlowGuard, and sealed-body obligations when active runtime cards are
shortened for maintainability.

#### Scenario: Runtime card is shortened
- **WHEN** a runtime card is compressed for maintainability
- **THEN** required identity-boundary, runtime command, current fallback, FlowGuard
  work-order, and sealed-body instructions remain present
- **AND** no retired path is introduced or reworded as usable workflow.
