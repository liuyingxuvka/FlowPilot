## ADDED Requirements

### Requirement: Shallow-completion findings stay visible through protected gates
FlowPilot SHALL preserve task-specific shallow-completion findings through PM
self-interrogation, low-quality-success review, route planning, reviewer
challenge, and terminal closure until PM dispositions them with current
evidence, route ownership, a scoped waiver, or a blocker.

#### Scenario: PM tries to activate route with unowned shallow trap
- **WHEN** self-interrogation or product architecture identifies a current
  shallow-completion traps
- **AND** PM route planning does not bind it to route work, evidence, a scoped
  waiver, or a blocker
- **THEN** the route SHALL be treated as not ready for activation.

#### Scenario: Trap is waived only for bounded planning output
- **WHEN** PM waives shallow-completion traps because the accepted user outcome
  is planning-only
- **THEN** the waiver SHALL preserve that boundary through final report and
  closure
- **AND** downstream gates SHALL NOT claim runnable, operational, or
  implementation-ready completion from that waiver.
