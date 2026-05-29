## ADDED Requirements

### Requirement: Full-System Completion Boundary

FlowPilot maintenance documentation and completion gates SHALL distinguish the
clean black-box runtime foundation from the complete FlowPilot system.

#### Scenario: Foundation checks are green

- **WHEN** the clean runtime foundation model, scenario tests, or install checks
  are green
- **THEN** maintenance reports MUST describe that confidence as scoped unless
  complete-system host, UI, migration, historical replay, and live-run evidence
  are also current.

### Requirement: Old Runtime As Reference Only

FlowPilot maintenance SHALL classify old runtime surfaces as reference,
negative-test, or diagnostic material unless a complete-system migration gate
explicitly imports them as read-only evidence.

#### Scenario: Old compatibility path appears in active surface

- **WHEN** an old compatibility alias, stale artifact, old route state, or old
  agent id appears in an active completion path
- **THEN** maintenance validation MUST block broad confidence until the path is
  removed, quarantined, or converted into read-only imported evidence.
