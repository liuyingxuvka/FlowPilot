## MODIFIED Requirements

### Requirement: PM considers process-support child skills
FlowPilot SHALL require Runtime to expose a current lightweight local skill/capability inventory and require PM to evaluate those candidates for both delivered product needs and FlowPilot process needs, including planning, specification, acceptance design, route design, validation, review, and modeling support, independently of whether extra material work is needed.

#### Scenario: Local planning skill is candidate-only but considered
- **WHEN** Runtime discovery finds a local planning, specification, review, modeling, or domain-analysis skill
- **THEN** PM child-skill selection records whether the skill is required, conditional, deferred, or rejected for product support or process support
- **AND** raw local availability remains non-authoritative.

#### Scenario: Process-support skill is not needed
- **WHEN** PM determines a local process-support skill does not improve the current route, evidence, or acceptance confidence
- **THEN** PM records a deferred or rejected decision with a reason instead of silently omitting the candidate or creating a route branch.

## ADDED Requirements

### Requirement: Skill inventory is shallow until PM selection
Runtime SHALL inventory candidate identity, path, availability, and basic dependency/version facts without deeply loading every skill; PM-selected skills SHALL use the existing skill-standard path for full instruction/reference reading and evidence projection.

#### Scenario: Many local skills are available
- **WHEN** discovery finds skills that are unrelated to the current project
- **THEN** Runtime SHALL still list them as candidates where applicable
- **AND** PM SHALL reject or defer them without loading their full references into every role context.
