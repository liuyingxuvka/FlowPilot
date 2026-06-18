## ADDED Requirements

### Requirement: Reviewer reports use a strict text-only quality score
FlowPilot SHALL instruct Reviewer to include a strict quality score in existing
review body text fields without adding a new runtime score field.

#### Scenario: Reviewer writes score line in existing fields
- **WHEN** Reviewer submits a formal review report
- **THEN** the report guidance MUST require a concise score line such as
  `Quality score: X/10; target: 9/10; minimum hard gate passed: true|false`
- **AND** the score line MUST be placed in existing fields such as
  `pm_visible_summary`, `findings`, `blockers`, or `pm_suggestion_items`.

#### Scenario: Score scale is high-standard
- **WHEN** Reviewer assigns a score
- **THEN** `6/10` MUST mean the minimum user standard is just met
- **AND** `9/10` MUST mean the high-quality FlowPilot target is met
- **AND** `10/10` MUST mean the result substantially exceeds the user's
  standard.

#### Scenario: Score is not a runtime schema field
- **WHEN** Runtime exposes the review result contract
- **THEN** the contract MUST NOT require a top-level `score`, `quality_score`,
  `scorecard`, or equivalent score field
- **AND** missing score text MUST NOT be repaired by adding a new runtime field.

### Requirement: Reviewer separates quality score from hard blockers
FlowPilot SHALL keep Reviewer scores separate from Reviewer hard-blocker
authority.

#### Scenario: Soft low score becomes PM decision support
- **WHEN** Reviewer scores a result below `9/10`
- **AND** the current minimum hard gate is met
- **THEN** Reviewer MUST record the gap as PM decision-support in existing
  review text or `pm_suggestion_items`
- **AND** Reviewer MUST NOT classify the score alone as a
  `current_gate_blocker`.

#### Scenario: Quantitative underdelivery blocks the gate
- **WHEN** the current packet, contract, PM instruction, or acceptance item
  requires an explicit quantity such as item count, word count, coverage rows,
  required ids, named sections, test/evidence count, or matrix rows
- **AND** the delivered artifact falls short of that current quantity
- **THEN** Reviewer MUST block the current gate
- **AND** the blocker MUST state the required quantity, delivered quantity,
  gap, and concrete PM-actionable repair.

#### Scenario: Recheck consumes score context
- **WHEN** Reviewer rechecks repaired evidence after a prior scored report
- **THEN** Reviewer MUST read the prior Reviewer report, PM disposition, repair
  packet, producer result, and current authorized evidence
- **AND** Reviewer MUST state whether the prior score gap, quantitative gap, or
  blocker was addressed.
