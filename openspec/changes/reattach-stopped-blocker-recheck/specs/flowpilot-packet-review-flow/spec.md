## MODIFIED Requirements

### Requirement: Review blockers clear only through fresh passing review evidence
FlowPilot review blockers SHALL clear only after the relevant Reviewer-owned
recheck returns a fresh passing result for the current repaired evidence path.

#### Scenario: Reattached review blocker requires fresh reviewer pass
- **WHEN** a stopped review blocker is reattached after evidence repair
- **THEN** FlowPilot issues a fresh Reviewer packet and waits for Reviewer pass
  before clearing the blocker.
