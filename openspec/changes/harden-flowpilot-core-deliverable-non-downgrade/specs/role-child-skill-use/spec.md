## ADDED Requirements

### Requirement: Child Skills Inherit Parent Deliverable Standards
FlowPilot SHALL require selected child-skill use to inherit the parent node's user-intent deliverable, scope, quantity, quality, material/evidence, and prohibition standards when those standards affect the child-skill output.

#### Scenario: Child skill returns weaker output
- **WHEN** a selected child skill returns an inventory, status label, partial result, report-only output, or lower-quality artifact that does not satisfy the parent node's required deliverable
- **THEN** PM or Reviewer SHALL treat the child output as blocker, repair, research, route mutation, or user clarification evidence rather than parent-node completion.

#### Scenario: Child standard is stricter
- **WHEN** a selected child skill has a stricter applicable standard than the PM's draft node plan
- **THEN** PM and Reviewer SHALL preserve the stricter standard unless it is explicitly waived through the existing waiver authority.
