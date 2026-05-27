# role-child-skill-use Specification

## Purpose
TBD - created by archiving change expand-role-child-skill-use. Update Purpose after archive.
## Requirements
### Requirement: PM considers process-support child skills
FlowPilot SHALL require the project manager to evaluate selected child skills for both delivered product needs and FlowPilot process needs, including planning, specification, acceptance design, route design, validation, review, and modeling support.

#### Scenario: Local planning skill is candidate-only but considered
- **WHEN** material intake finds a local planning, specification, review, modeling, or domain-analysis skill
- **THEN** PM child-skill selection records whether the skill is required, conditional, deferred, or rejected for product support or process support, with raw local availability remaining non-authoritative

#### Scenario: Process-support skill is not needed
- **WHEN** PM determines a local process-support skill does not improve the current route, evidence, or acceptance confidence
- **THEN** PM records a deferred or rejected decision with a reason instead of silently omitting the candidate

### Requirement: Selected child skills name role-scoped use
FlowPilot SHALL represent each meaningful selected child-skill use with role-scoped bindings that name the skill, source path, user role, use context, reason, evidence requirements, and review or approval authority.

#### Scenario: PM uses a planning child skill
- **WHEN** PM selects a child skill to support planning, route design, or acceptance criteria
- **THEN** the child-skill manifest or node plan includes a role-skill binding for `project_manager`, the planning context, source skill paths, expected evidence, and who checks that evidence

#### Scenario: Reviewer or officer uses a child skill
- **WHEN** reviewer or a FlowGuard officer is assigned a selected child skill for review, modeling, validation, or gate analysis
- **THEN** the relevant gate plan records that role as the skill user and names the evidence that role must leave

### Requirement: Role skill use leaves reviewer-checkable evidence
FlowPilot SHALL require role-skill-use evidence whenever a selected child skill materially affects a role's formal output, gate decision, review, model, route plan, acceptance criteria, or validation.

#### Scenario: Assigned role uses selected skill
- **WHEN** a formal role uses a selected child skill under a role-skill binding
- **THEN** the role output includes Role Skill Use Evidence showing source skill paths opened, applicable standards or workflow steps used, outputs influenced, waivers or skips, and evidence paths

#### Scenario: Assigned role omits selected skill evidence
- **WHEN** a role was assigned selected skill use but returns only prose or a completion claim
- **THEN** reviewer or the relevant gate check blocks or requests repair rather than treating self-attestation as evidence

### Requirement: Worker child-skill evidence remains intact
FlowPilot SHALL preserve the existing worker-focused `Child Skill Use Evidence` path while adding role-general skill-use evidence for PM, reviewer, officer, or other formal role usage.

#### Scenario: Worker executes a skill-bound packet
- **WHEN** a worker packet declares active child-skill bindings
- **THEN** the worker still returns `Child Skill Use Evidence` for every active binding and the reviewer still checks source-skill opening, node-slice fit, and stricter-standard precedence

#### Scenario: PM planning skill and worker execution skill both apply
- **WHEN** PM uses one selected skill for planning and a worker uses another selected skill for execution
- **THEN** PM's formal output includes Role Skill Use Evidence and the worker result includes Child Skill Use Evidence, with neither evidence type replacing the other

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

### Requirement: PM considers FlowGuard satellite skills as process support
FlowPilot SHALL make FlowGuard satellite skills visible to PM as process-support candidates during child-skill selection.

#### Scenario: PM reviews child-skill candidates
- **WHEN** PM evaluates local skills for child-skill selection
- **THEN** the selection guidance includes FlowGuard satellite skills as process-support candidates without creating a separate trigger matrix or gate family
