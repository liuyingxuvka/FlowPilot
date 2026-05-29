## ADDED Requirements

### Requirement: Old Reviewer Dispatch Is Retired Audit History
FlowPilot SHALL treat old reviewer-dispatch cards, events, or flags as retired audit
history only.

#### Scenario: Old reviewer dispatch flag is present
- **WHEN** a run contains an old reviewer-dispatch flag from historical data
- **THEN** Router and PM package gates ignore it for current package disposition,
  formal gate package release, and Reviewer package-review acceptance
- **AND** active prompts and specs SHALL NOT describe that flag as compatibility
  evidence for current callers.
