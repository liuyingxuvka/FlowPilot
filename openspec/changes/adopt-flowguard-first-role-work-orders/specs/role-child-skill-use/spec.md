## ADDED Requirements

### Requirement: Role skill bindings distinguish FlowGuard satellite routes
FlowPilot SHALL represent FlowGuard satellite routes as process-support role
skill bindings without reclassifying FlowGuard itself as an optional ordinary
child skill.

#### Scenario: PM selects FlowGuard for role process work
- **WHEN** PM determines that a role's planning, modeling, validation, review,
  repair, or completion-readiness work should use FlowGuard
- **THEN** the binding SHALL name the role, FlowGuard route, source skill path,
  work-order id, affected output or gate, evidence required, and reviewer or
  PM check authority
- **AND** the binding SHALL NOT list FlowGuard as an ordinary deliverable child
  skill whose standards replace product/process model coverage.

#### Scenario: Ordinary child skill and FlowGuard route both apply
- **WHEN** a Worker uses an ordinary child skill and a FlowGuard report assigns
  validation obligations to the same packet
- **THEN** the packet SHALL preserve both ordinary Child Skill Use Evidence and
  FlowGuard obligation coverage
- **AND** neither evidence type SHALL replace the other.

### Requirement: Every formal role can consume FlowGuard work orders
FlowPilot SHALL allow PM, Product Officer, Process Officer, Reviewer, and
Workers to consume FlowGuard work-order/report references according to their
existing authority boundary.

#### Scenario: Reviewer checks FlowGuard role-skill evidence
- **WHEN** a review gate depends on a role's FlowGuard route use
- **THEN** Reviewer SHALL check Role Skill Use Evidence for source paths,
  work-order id, route used, report id, freshness, skips, and affected gate
- **AND** missing self-contained evidence SHALL block the gate or require PM
  repair instead of passing on self-attestation.

#### Scenario: Worker returns assigned FlowGuard coverage
- **WHEN** a packet declares FlowGuard obligations, report references, or
  work-order-derived validation rows
- **THEN** the Worker result SHALL include coverage rows for each assigned
  obligation, including evidence, freshness, skipped or failed checks, and
  remaining out-of-scope gaps.
