## ADDED Requirements

### Requirement: PM owns source-intent preservation and repair
FlowPilot SHALL require PM prompts to preserve concrete user requirements in
the product architecture, root contract, node acceptance plans, final ledger,
and closure decision without delegating semantic interpretation to runtime.

#### Scenario: PM repairs semantic dilution
- **WHEN** Reviewer blocks a package because concrete user intent was lost,
  weakened, or replaced by generic acceptance wording
- **THEN** PM SHALL repair by rereading the authorized source material and
  rewriting the current acceptance, route, node, or final-ledger surface
- **AND** PM SHALL NOT close the blocker with explanatory prose, report-only
  evidence, or a runtime/mechanical waiver.

### Requirement: Reviewer remains anti-repair while enforcing quality
FlowPilot SHALL require Reviewer prompts to enforce source-intent and product
quality through pass/block/request-repair decisions without giving Reviewer
authority to modify the artifact under review.

#### Scenario: Reviewer blocks without direct repair
- **WHEN** Reviewer finds source-intent loss, a semantic downgrade, missing
  product evidence, or final artifact drift
- **THEN** Reviewer SHALL return a blocker, more-evidence request, or PM
  routing recommendation
- **AND** Reviewer SHALL NOT directly edit the worker output, PM package,
  route, final artifact, or acceptance contract under review.

### Requirement: Worker output evidence must address the accepted task
FlowPilot SHALL require worker-result review prompts to reject completion that
only proves activity or artifact existence without proving the accepted task
slice.

#### Scenario: Existence-only worker result is insufficient
- **WHEN** a worker result claims completion from a file, report, screenshot,
  command, model, or ledger row existing
- **AND** that evidence does not directly show the accepted task slice was
  satisfied
- **THEN** Reviewer SHALL block or request repair using existing review fields.
