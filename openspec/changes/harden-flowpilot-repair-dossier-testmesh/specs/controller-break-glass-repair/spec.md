## MODIFIED Requirements

### Requirement: Five same-parent repair nodes without recovery enter break-glass
FlowPilot SHALL enter Controller break-glass when a repair dossier reaches five
consecutive same-parent repair nodes without recovery to a normal non-repair
business node.

#### Scenario: Fifth repair node triggers break-glass
- **GIVEN** an active repair dossier has the same parent node
- **AND** five consecutive repair nodes have been opened without normal
  business-node recovery
- **WHEN** Runtime would issue another ordinary PM repair packet or repair node
- **THEN** Runtime MUST expose Controller break-glass
- **AND** Runtime MUST NOT issue another ordinary repair packet for that
  dossier.

#### Scenario: Normal business recovery resets repair depth
- **GIVEN** an active repair dossier has fewer than five repair nodes
- **WHEN** the route reaches and accepts a normal non-repair business node
- **THEN** Runtime MUST mark normal recovery for the dossier
- **AND** later unrelated blockers MUST start a new repair count.

#### Scenario: PM plan acceptance is not recovery
- **WHEN** a PM node acceptance plan passes review inside a repair dossier
- **THEN** Runtime MUST NOT mark the dossier as normally recovered.

#### Scenario: Superseded route-mutation blockers still count
- **WHEN** old blockers in the dossier are superseded by route mutation
- **THEN** Runtime MUST still count their repair nodes toward the five-node
  threshold until normal recovery or explicit dossier closure occurs.
