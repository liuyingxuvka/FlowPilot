## ADDED Requirements

### Requirement: Parent frontier cannot advance before current closure review
FlowPilot SHALL keep a parent/module node on the current route frontier until
that node's current parent backward review has passed and PM has recorded an
absorbing `continue` parent segment decision.

#### Scenario: Sibling waits for parent closure
- **WHEN** a parent/module node has completed child work
- **AND** its current parent backward review or PM absorption is not complete
- **THEN** FlowPilot SHALL keep the parent/module node as the current closure
  frontier
- **AND** FlowPilot SHALL NOT open the next sibling or ancestor route node

#### Scenario: Repair reruns the same parent review
- **WHEN** a parent backward review blocks and PM repairs a child, sibling, or
  subtree
- **THEN** FlowPilot SHALL stale the affected parent/module closure evidence
- **AND** FlowPilot SHALL rerun the same parent backward review before route
  progression resumes
