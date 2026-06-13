## ADDED Requirements

### Requirement: PM implementation intent precedes route skeleton

FlowPilot SHALL require a PM-authored implementation intent brief after PM accepts the product behavior model and before PM drafts a route skeleton, unless a strict simple-task waiver is recorded.

#### Scenario: Product model accepted

- **WHEN** PM accepts the product behavior model for a non-trivial task
- **THEN** the next legal planning step is PM implementation intent, not route skeleton drafting

#### Scenario: Route skeleton attempted early

- **WHEN** route skeleton drafting is attempted before required implementation intent acceptance
- **THEN** Runtime/Router rejects the transition and keeps the current planning state blocked at the implementation-intent gate

### Requirement: PM intent is guidance, not a formal FlowGuard model

FlowPilot SHALL require the PM implementation intent brief to describe realization guidance without authoring formal FlowGuard states, transitions, or executable model results.

#### Scenario: PM submits implementation intent

- **WHEN** PM submits implementation intent
- **THEN** the artifact includes selected realization path, alternatives considered, hard parts, thin-success traps, non-downgrade rules, evidence needs, FlowGuard questions, failure policy, and route implications

#### Scenario: PM submits a formal model instead

- **WHEN** PM implementation intent is a formal FlowGuard model or substitutes states/transitions for PM realization judgment
- **THEN** the submission is rejected as role-boundary leakage

### Requirement: FlowGuard target-realization model formalizes PM intent

FlowPilot SHALL require FlowGuard Operator to build a target-realization model from the PM implementation intent, accepted product behavior model, and product architecture.

#### Scenario: FlowGuard target-realization model submitted

- **WHEN** FlowGuard Operator submits the target-realization report
- **THEN** the report includes modeled realization states, transition map, hazards, counterexamples, progress/stuck review, evidence gates, downstream obligations, and residual blindspots

#### Scenario: FlowGuard model ignores PM intent

- **WHEN** the target-realization report does not cite or preserve the PM implementation intent
- **THEN** the report is rejected and route skeleton remains blocked

### Requirement: PM and Reviewer accept target realization before route drafting

FlowPilot SHALL require PM acceptance and Reviewer challenge of the target-realization model before route skeleton drafting can proceed.

#### Scenario: PM accepts and Reviewer passes

- **WHEN** PM accepts the target-realization model and Reviewer passes the implementation-intent challenge
- **THEN** route skeleton drafting may proceed with accepted realization obligations available as route inputs

#### Scenario: PM or Reviewer blocks

- **WHEN** PM requests model rebuild, PM rewrites intent, or Reviewer blocks alignment
- **THEN** route skeleton drafting remains illegal until the implementation-intent loop returns to an accepted state

### Requirement: Realization obligations propagate to downstream work

FlowPilot SHALL project accepted realization obligations into route skeletons, route-process checks, node acceptance plans, worker packets, and final closure ledgers.

#### Scenario: Node plan inherits obligations

- **WHEN** PM writes a node acceptance plan
- **THEN** the plan names the accepted realization obligations and thin-success traps that the node must satisfy or avoid

#### Scenario: Final closure omits obligations

- **WHEN** terminal closure is attempted without closing, waiving, or superseding accepted realization obligations
- **THEN** final closure is blocked as incomplete
