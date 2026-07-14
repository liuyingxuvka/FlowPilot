## ADDED Requirements

### Requirement: Local capability and skill discovery remains mandatory
FlowPilot SHALL keep one mandatory lightweight `task.discovery` step that inventories current local skills, capability paths, availability, and relevant environment constraints before PM selects process or deliverable support.

#### Scenario: Runtime issues discovery
- **WHEN** a high-standard FlowPilot run reaches discovery
- **THEN** Runtime SHALL project the current local capability/skill inventory into the existing discovery packet
- **AND** PM SHALL classify the candidate skills before route planning.

#### Scenario: Only selected skills are deeply loaded
- **WHEN** PM marks a candidate skill required or conditional
- **THEN** the existing skill-standard path SHALL open the selected `SKILL.md` and applicable references and project their standards into role-scoped evidence
- **AND** rejected or deferred candidates SHALL NOT cause deep loading or new route branches.

### Requirement: Discovery no longer requires material sufficiency fields
The current `task.discovery` positive result SHALL require only the discovery decision and candidate skill inventory needed by the current capability-selection path; `material_sources` and `material_sufficiency` SHALL be deleted from its positive contract without aliases, defaults, or translation.

#### Scenario: Current discovery omits old material fields
- **WHEN** PM submits a current discovery result with the current required fields
- **THEN** Runtime SHALL accept it without a material source list or material sufficiency declaration.

#### Scenario: Old material-shaped discovery is submitted
- **WHEN** a result relies on `material_sources` or `material_sufficiency` as current discovery authority
- **THEN** Runtime SHALL reject the unsupported current-contract shape or ignore it only where an explicit deleted-field negative contract requires rejection
- **AND** SHALL NOT translate it into a valid current result.

### Requirement: Additional material work uses ordinary role-work packets
PM SHALL read ordinary available non-sealed project material directly and SHALL issue missing reading, research, experiment, source verification, or evidence work through the existing general PM role-work request/batch path rather than a mandatory special material-scan packet or startup gate.

#### Scenario: PM needs deeper source analysis
- **WHEN** PM cannot responsibly decide product architecture, route, acceptance, or validation from currently available understanding
- **THEN** PM SHALL issue one or more bounded ordinary role-work packets with explicit evidence outcomes
- **AND** absorb their results through the existing PM disposition and risk-appropriate review path.

#### Scenario: Existing material is already sufficient
- **WHEN** PM can establish the required product and route decisions by reading current material directly
- **THEN** FlowPilot SHALL proceed without creating a material-scan form, dedicated material-sufficiency review, or material-only route node.

### Requirement: Material navigation remains optional and non-authoritative
FlowPilot MAY derive a material artifact map when a long project benefits from reusable navigation, but the map SHALL remain optional, index-only, and incapable of granting access or satisfying acceptance.

#### Scenario: No material map exists
- **WHEN** a run has no derived material artifact map
- **THEN** startup, planning, route activation, ordinary role work, review, and closure SHALL remain legal when their actual required evidence is present.
