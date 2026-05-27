## ADDED Requirements

### Requirement: Role-skill bindings reference modeling coverage when they affect models
FlowPilot SHALL bind role-skill use to the run's modeling coverage artifacts when a selected child skill or FlowGuard route materially affects a formal model, model report, route gate, or validation claim.

#### Scenario: Officer uses FlowGuard skill route for a planned model family
- **WHEN** PM assigns Product FlowGuard Officer or Process FlowGuard Officer a FlowGuard skill route from the startup capability snapshot
- **THEN** the role-skill binding SHALL reference the `flowguard_capability_snapshot_id`, the relevant PM modeling plan, the skill source path, and evidence the officer must leave.

#### Scenario: PM uses ordinary child skill standards in modeling plans
- **WHEN** PM maps an ordinary child skill into Product Modeling Plan or Process Modeling Plan coverage
- **THEN** the binding SHALL state whether the child skill affects product behavior, process route design, validation, reviewer gates, officer gates, worker packets, or final ledger closure.

#### Scenario: Role output omits modeling-bound skill evidence
- **WHEN** a role output relies on a modeling-bound skill use but omits Role Skill Use Evidence
- **THEN** PM or Reviewer SHALL block the model decision, route activation, or closure gate instead of accepting self-attestation.
