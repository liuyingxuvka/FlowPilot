## ADDED Requirements

### Requirement: PM requests terminal FlowGuard coverage before closure

FlowPilot SHALL require the PM to issue a `terminal_flowguard_coverage_review`
FlowGuard operator Work Order after effective node, parent, and route backward
replay evidence is settled and before PM terminal closure can pass.

#### Scenario: Terminal coverage request is missing

- **WHEN** PM final ledger or terminal closure is evaluated for a non-trivial
  FlowGuard-backed run
- **THEN** FlowPilot MUST reject closure if no current
  `terminal_flowguard_coverage_review` Work Order is recorded.

#### Scenario: Terminal coverage request precedes settled replay

- **WHEN** a terminal coverage Work Order is recorded before effective
  node/parent backward replay evidence is settled
- **THEN** FlowPilot MUST report the coverage request as premature or stale.

### Requirement: FlowGuard operator reports terminal project coverage

FlowPilot SHALL require the FlowGuard operator terminal coverage report to
identify the modeled terminal boundary, current route version, root contract,
acceptance items, route nodes examined, FlowGuard-required coverage items,
coverage evidence found, missing or stale evidence, model-test alignment gaps,
blockers, PM suggestions, waivers, and evidence references.

#### Scenario: Report omits coverage matrix

- **WHEN** a FlowGuard operator terminal coverage report omits required terminal
  coverage matrix or evidence references
- **THEN** FlowPilot MUST reject the report for terminal closure evidence.

#### Scenario: Report is progress-only

- **WHEN** a FlowGuard operator result contains only progress, intent, or
  checklist text without terminal coverage evidence and self-check fields
- **THEN** FlowPilot MUST classify it as progress-only and not as pass evidence.

### Requirement: PM absorbs and dispositions terminal coverage

FlowPilot SHALL require PM final ledger to record
`flowguard_terminal_coverage_closure` with the terminal report id, Work Order
id, route version, freshness status, PM acceptance decision, unresolved
blockers, unresolved PM suggestions, waivers, and supplemental repair
decisions.

#### Scenario: PM has not accepted current report

- **WHEN** the terminal coverage report exists but PM has not accepted,
  dispositioned, repaired, waived, or stopped on its findings
- **THEN** FlowPilot MUST block final ledger completion and terminal closure.

#### Scenario: Suggestions remain pending

- **WHEN** terminal coverage PM suggestion items remain pending in the PM
  suggestion ledger
- **THEN** FlowPilot MUST block terminal closure until each item is adopted,
  repaired, redesigned, deferred, rejected, waived, stopped, or recorded with a
  PM decision.

### Requirement: Reviewer terminal replay checks FlowGuard governance

FlowPilot SHALL include a `flowguard-coverage-governance` segment in terminal
Reviewer backward replay that verifies the current terminal coverage report,
PM absorption, blocker disposition, suggestion disposition, freshness, and
waiver evidence.

#### Scenario: Reviewer replay lacks coverage segment

- **WHEN** terminal backward replay passes without a
  `flowguard-coverage-governance` segment for a non-trivial FlowGuard-backed
  run
- **THEN** FlowPilot MUST reject the replay as incomplete.

#### Scenario: Reviewer segment finds stale coverage

- **WHEN** the Reviewer segment finds a stale, missing, unaccepted, or blocking
  terminal FlowGuard coverage report
- **THEN** FlowPilot MUST return a terminal blocker to PM instead of allowing
  PM terminal closure.

### Requirement: Coverage gaps use supplemental repair contracts

FlowPilot SHALL route missing, stale, unaccepted, progress-only, or blocking
terminal FlowGuard coverage through the existing PM supplemental repair
contract loop using `gap_kind=flowguard_coverage_gap` or an explicitly
equivalent final-artifact hygiene model coverage category.

#### Scenario: Missing report requires operator repair

- **WHEN** terminal review finds no usable terminal coverage report
- **THEN** PM MUST create or reissue a FlowGuard operator-owned supplemental
  repair item before closure can continue.

#### Scenario: Target project gap requires worker repair

- **WHEN** terminal coverage finds real target project, test, documentation, or
  validation gaps outside the operator report itself
- **THEN** PM MUST route those gaps to worker/test repair nodes rather than
  letting the FlowGuard operator directly repair target project content.

### Requirement: Runtime tests cover fake response and cartesian hazards

FlowPilot SHALL include model-scoped finite-axis coverage for terminal
FlowGuard coverage hazards and SHALL project accepted cartesian cases into
runtime tests using fake role-output responses where appropriate.

#### Scenario: Scattered node evidence attempts to substitute terminal report

- **WHEN** fake PM/reviewer evidence contains node-level FlowGuard reports but
  no current terminal coverage report
- **THEN** runtime tests MUST prove terminal closure is blocked.

#### Scenario: Cartesian hazard matrix is exercised

- **WHEN** report presence, freshness, PM acceptance, blocker state,
  suggestion state, reviewer segment state, and repair routing axes are
  combined in the focused model
- **THEN** accepted unsafe combinations MUST have current runtime or model-test
  evidence and MUST NOT be claimed only from prose.

