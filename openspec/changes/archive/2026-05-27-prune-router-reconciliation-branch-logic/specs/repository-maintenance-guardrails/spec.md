## ADDED Requirements

### Requirement: Structure optimization prioritizes branch-risk reduction

Repository maintenance SHALL treat file splitting as a secondary technique
behind behavior-preserving logic contraction, duplicate-branch removal, and
bug-risk reduction.

#### Scenario: Line count alone does not justify a split

- **WHEN** a FlowPilot owner module exceeds a line-count threshold
- **THEN** the maintenance plan identifies the behavior-bearing branch risk,
  duplicate result paths, or ownership ambiguity being reduced
- **AND** it does not claim a maintenance improvement solely because code moved
  into more files.

#### Scenario: Branch pruning drives structure planning

- **WHEN** FlowGuard Architecture Reduction identifies repeated branches around
  the same observable state or side effects
- **THEN** Code Structure Recommendation derives target modules from the
  reduced FunctionBlocks, state ownership, side-effect ownership, and public
  compatibility boundary.

#### Scenario: Risky state owners remain explicit

- **WHEN** a candidate touches core runtime state, stale-save protection,
  dynamic Router event authority, or external event recording
- **THEN** the plan records the missing evidence or replay requirement
- **AND** the candidate remains blocked or model-only until that evidence is
  supplied.
