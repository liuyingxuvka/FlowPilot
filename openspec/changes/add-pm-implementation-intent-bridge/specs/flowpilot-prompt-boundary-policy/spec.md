## ADDED Requirements

### Requirement: Implementation intent preserves role boundaries

FlowPilot prompt cards SHALL preserve the role split where PM writes implementation intent guidance, FlowGuard Operator writes formal target-realization models, Reviewer challenges quality and alignment, and Runtime/Router enforces mechanical legality.

#### Scenario: Prompt card asks PM for formal modeling

- **WHEN** a PM prompt card for implementation intent asks PM to author formal FlowGuard states, transitions, or executable checks
- **THEN** prompt coverage validation fails as PM/FlowGuard role leakage

#### Scenario: Prompt card asks Reviewer to model

- **WHEN** a Reviewer prompt card asks Reviewer to build the formal target-realization model instead of challenging the PM/FlowGuard alignment
- **THEN** prompt coverage validation fails as Reviewer role leakage
