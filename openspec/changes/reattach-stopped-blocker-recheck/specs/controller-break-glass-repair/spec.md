## MODIFIED Requirements

### Requirement: Break-glass repair returns to normal control through recheck
FlowPilot Controller break-glass repair SHALL exit by restoring a legal
runtime next action and SHALL NOT directly approve route gates, clear semantic
blockers, or replace the required FlowGuard/Reviewer owner decision.

#### Scenario: Break-glass repairs stopped blocker cause
- **WHEN** Controller break-glass repairs a control-plane or evidence-runner
  defect that caused a stopped semantic blocker
- **THEN** Controller returns to normal flow through
  `resolve-stopped-blocker --resolution reattach_required_recheck` after user
  request, and the required owner recheck decides whether the blocker clears.
