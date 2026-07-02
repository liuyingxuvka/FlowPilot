## MODIFIED Requirements

### Requirement: Same-root unresolved blockers count through break-glass
FlowPilot SHALL count same-root repair blockers toward the break-glass threshold
until current lineage evidence proves the root cause is closed, even if older
blocker rows were marked cleared by a repair outcome.

#### Scenario: Cleared but unclosed blocker still counts
- **GIVEN** a blocker has the same `root_cause_loop_key` as the current blocker
- **AND** the older blocker has `cleared_by_outcome_id`
- **AND** there is no current lineage closure evidence for that root cause
- **WHEN** Runtime computes the repair-loop count
- **THEN** the older blocker MUST still count toward the same-root attempt count.

#### Scenario: Verified lineage closure stops counting
- **GIVEN** a same-root blocker has current `lineage_verified_closed_by` evidence
- **WHEN** Runtime computes the repair-loop count for a later unrelated blocker
- **THEN** the closed blocker MUST NOT count toward the later repair loop.

#### Scenario: More than five same-root attempts enters break-glass
- **GIVEN** more than five unresolved same-root blocker attempts exist
- **WHEN** another ordinary PM repair packet would be issued
- **THEN** Runtime MUST expose Controller break-glass duty
- **AND** Runtime MUST NOT issue another ordinary PM repair packet for that root cause.
