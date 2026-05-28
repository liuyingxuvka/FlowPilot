## ADDED Requirements

### Requirement: FlowPilot records FlowGuard work orders for non-trivial role judgement
FlowPilot SHALL represent non-trivial product, process, skill, acceptance,
validation, evidence-freshness, repair, resume, and closure questions as
run-scoped FlowGuard work orders before the dependent PM decision, reviewer
gate, worker packet, or terminal closure can rely on FlowGuard-backed
judgement.

#### Scenario: PM creates a FlowGuard work order before route judgement
- **WHEN** PM must decide route structure, product behavior, process viability,
  node acceptance, repair return path, validation freshness, or final closure
- **THEN** the PM artifact SHALL cite a `flowguard_work_order_id` or record a
  scoped `flowguard_not_required_reason`
- **AND** the cited work order SHALL name the question, role owner, FlowGuard
  route or satellite skill requested, source artifacts, output contract,
  affected gate, expected report path, and freshness rule.

#### Scenario: Trivial work is explicitly scoped out
- **WHEN** a PM or role artifact claims FlowGuard is not required
- **THEN** it SHALL record why the work is trivial, mechanical, already covered
  by current evidence, or outside behavior/process/evidence risk
- **AND** that reason SHALL NOT grant permission to skip FlowGuard for route,
  product, repair, validation, or completion decisions.

### Requirement: FlowGuard reports answer work orders with evidence boundaries
FlowPilot SHALL require FlowGuard reports to answer the exact work order and
expose evidence, skipped checks, freshness, and confidence boundaries.

#### Scenario: Officer returns a work-order-bound report
- **WHEN** Product FlowGuard Officer or Process FlowGuard Officer returns a
  formal report
- **THEN** the report SHALL cite `flowguard_work_order_id`,
  `flowguard_route_used`, source paths opened, model boundary, commands or
  checks run, skipped checks with reasons, evidence refs, confidence boundary,
  residual blindspots, and PM decision impact.

#### Scenario: Progress-only evidence cannot complete a report
- **WHEN** a report cites a long or background check
- **THEN** the report SHALL include background artifact completion fields for
  log root, stdout, stderr, combined output, exit artifact, meta artifact, exit
  code, latest update time, completion status, and proof reuse
- **AND** progress output alone SHALL NOT count as a passing FlowGuard report.

### Requirement: FlowGuard status references are safe to relay
FlowPilot SHALL carry compact FlowGuard status references through prompts,
packets, events, ledgers, and Controller-visible metadata without exposing
sealed report bodies.

#### Scenario: Controller resumes with FlowGuard status only
- **WHEN** Controller resumes a run or recovers from break-glass
- **THEN** Controller MAY surface FlowGuard work-order/report ids, paths,
  hashes, freshness status, owner role, and pending/blocking state
- **AND** Controller SHALL NOT interpret report contents, approve gates,
  mutate routes, or replace PM/Reviewer/Officer judgement.

#### Scenario: Event cards preserve work-order traceability
- **WHEN** PM node-started, reviewer-report, or reviewer-blocked events involve
  FlowGuard-backed gates
- **THEN** the event artifact SHALL include the relevant work-order/report ids
  or state why no FlowGuard work order applied
- **AND** downstream PM decisions SHALL treat stale, missing, or blocked
  FlowGuard status as unresolved until repaired or waived with authority.

### Requirement: FlowGuard work orders preserve role authority
FlowPilot SHALL keep FlowGuard work-order execution inside the addressed role's
existing authority boundary.

#### Scenario: Officer report does not approve the route
- **WHEN** an Officer completes a FlowGuard work order
- **THEN** the report MAY recommend pass, repair, reroute, more evidence,
  TestMesh, Model-Test Alignment, StructureMesh, Model Miss Review, or block
- **AND** it SHALL NOT approve gates, mutate routes, close nodes, or make PM
  decisions by itself.

#### Scenario: Worker reports packet-scoped coverage
- **WHEN** a Worker receives FlowGuard-derived obligations in a packet
- **THEN** the Worker SHALL satisfy only the assigned packet-scoped obligations
  or return `blocked`, `needs_pm`, or PM Suggestion Items for broader work
- **AND** the Worker SHALL NOT create new route structure or accept/waive
  FlowGuard gates.
