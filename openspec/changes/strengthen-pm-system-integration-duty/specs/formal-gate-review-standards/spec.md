## ADDED Requirements

### Requirement: Integration review findings keep hard and advisory classes separate
FlowPilot SHALL classify integration review findings using existing blocker and PM suggestion mechanisms.

#### Scenario: Hard integration failure blocks through existing fields
- **WHEN** Reviewer or FlowGuard finds unmet explicit requirements, missing proof, semantic downgrade, route-order impossibility, role-boundary failure, protocol violation, unusable parent composition, or root-goal failure
- **THEN** the finding SHALL use existing blocked review or current-gate-blocker mechanisms.

#### Scenario: Higher-standard integration improvement stays PM support
- **WHEN** Reviewer or FlowGuard finds a simpler equivalent structure, cleaner order, optional deduplication, or higher-quality callback that does not prove the current gate minimum is unmet
- **THEN** the finding SHALL be a PM decision-support item, nonblocking note, or FlowPilot skill improvement observation.

#### Scenario: Reviewer quality score below nine is not automatic blocker
- **WHEN** the current minimum gate passes but Reviewer scores the artifact below the target quality ceiling
- **THEN** the score SHALL inform PM optimization judgement and SHALL NOT automatically block.

### Requirement: Integration findings are repairable
FlowPilot SHALL require hard integration blockers to name the broken relation and the existing repair lane.

#### Scenario: Composition blocker names affected relation
- **WHEN** Reviewer blocks because children do not compose into the parent goal
- **THEN** the review SHALL identify the affected parent, child or sibling relation, missing bridge or conflict, and the existing PM repair lane.

#### Scenario: Final artifact blocker names root impact
- **WHEN** final backward replay blocks because the delivered artifact is scattered or incoherent
- **THEN** the review SHALL name the root acceptance or final-user intent impact and the current evidence that failed.
