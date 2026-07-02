# blocker-repair-policy Specification

## ADDED Requirements

### Requirement: PM repair packets state prior failure, required repair, and gate checks

PM repair decisions SHALL use existing current-contract fields to make the repair target concrete enough for downstream roles to execute and review without guessing.

#### Scenario: PM opens a blocker repair packet
- **WHEN** PM chooses a continuing repair path
- **THEN** the PM output MUST identify the prior failure, required repair, and expected Worker/FlowGuard/Reviewer checks in the existing repair decision text/context fields
- **AND** generic instructions such as "fix quality" or "repair the issue" are insufficient when the blocker contains named obligations.

### Requirement: Worker repair results answer blocker obligations item-by-item

Worker results SHALL explain how the current artifact/output changed relative to each requested repair obligation.

#### Scenario: Worker repairs a blocker with multiple named obligations
- **WHEN** the repair packet names multiple concrete obligations
- **THEN** the Worker result MUST address each obligation through existing summary/findings/evidence fields or the delivered artifact
- **AND** a generic "done" or "used the materials" claim MUST NOT support reviewer pass.

### Requirement: Repeated blocker repair remains normal until threshold, then glass-break

FlowPilot SHALL keep the existing five-attempt same-family/dossier break-glass threshold and SHALL NOT auto-clear blockers without verified normal recovery.

#### Scenario: Five consecutive same-family repair attempts fail to return to normal work
- **WHEN** the same blocker family/dossier reaches the configured threshold without normal business-node recovery
- **THEN** Controller break-glass diagnosis is required
- **AND** break-glass evidence does not itself approve the business artifact.
