## ADDED Requirements

### Requirement: Terminal closure emits a final user report

After clean terminal closure, FlowPilot SHALL write a durable final user report
artifact for the current run.

#### Scenario: Closure succeeds
- **WHEN** the final ledger, terminal human backward replay, and PM closure
  approval all pass
- **THEN** FlowPilot writes a final user report under the current run with
  outcome summary, delivered artifacts, validation evidence, unresolved risk
  status, and continuation status.

#### Scenario: Closure has unresolved blockers
- **WHEN** terminal closure is blocked or unresolved risks remain
- **THEN** FlowPilot does not write a successful final user report and instead
  keeps the closure blocker visible.

### Requirement: Final user report does not create completion authority

The final user report SHALL be output evidence only and MUST NOT substitute for
PM closure approval, final ledger cleanliness, or terminal backward replay.

#### Scenario: User report exists without PM closure
- **WHEN** a final user report file exists but PM closure approval is absent or
  stale
- **THEN** FlowPilot does not treat the run as terminally complete.

#### Scenario: Report references validation evidence
- **WHEN** the final user report is written
- **THEN** it references validation commands or evidence paths already accepted
  by the terminal closure process rather than inventing new pass claims.
