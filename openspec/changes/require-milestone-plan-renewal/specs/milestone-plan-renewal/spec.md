## Purpose

Defines the single current control loop that turns each completed major
milestone into a mandatory, independently challenged renewal of the complete
remaining plan before FlowPilot may continue toward the final user goal.

## ADDED Requirements

### Requirement: Top-level route nodes are unconditional major milestone gates
FlowPilot SHALL derive major milestones mechanically from current route
topology. Every route node with no parent SHALL enter the milestone-plan-renewal
gate when PM proposes to accept it; nested child nodes SHALL contribute to
their top-level parent but SHALL NOT independently trigger a global plan
renewal.

#### Scenario: Top-level leaf reaches PM acceptance
- **WHEN** PM proposes to accept a top-level leaf node
- **THEN** FlowPilot SHALL hold the execution frontier at that milestone
- **AND** SHALL require the current milestone-plan-renewal gate before exposing
  the next route node for execution.

#### Scenario: Top-level module closes after its children
- **WHEN** a top-level parent or module has current accepted children and passes
  its required backward-composition review
- **AND** PM proposes to accept the parent or module
- **THEN** FlowPilot SHALL enter exactly one milestone-plan-renewal gate for the
  top-level parent or module.

#### Scenario: Nested child closes
- **WHEN** PM accepts a nested child node
- **THEN** FlowPilot SHALL continue the existing parent-composition path
- **AND** SHALL NOT require a separate global remaining-plan rewrite for that
  nested child.

### Requirement: Milestone acceptance carries a current audit
Every top-level milestone acceptance SHALL include a structured current audit
that accounts for completed outcomes and evidence, deviations from prior
expectations, remaining goal gaps, the prior remaining plan's fitness, and the
rationale for the freshly submitted remaining plan.
The audit SHALL repeat the frozen final-goal `contract_hash`, identify every
completed top-level prefix row by `node_id`, and bind each remaining gap to one
or more submitted remaining-plan `owner_node_ids`.

#### Scenario: Milestone audit is complete
- **WHEN** PM submits a top-level milestone acceptance
- **THEN** the audit SHALL explicitly include `completed`, `deviations`,
  `remaining`, `prior_plan_assessment`, and `replan_rationale`
- **AND** each completed claim SHALL include its current top-level `node_id`
  and cite its complete runtime-issued evidence set
- **AND** `milestone_audit.contract_hash` SHALL match the frozen final-goal
  contract.

#### Scenario: No deviation occurred
- **WHEN** current evidence reveals no material deviation from the prior plan
- **THEN** PM SHALL still submit an explicit empty `deviations` collection
- **AND** SHALL still assess the prior plan and justify the new submission.

#### Scenario: Audit omits a required surface
- **WHEN** a top-level milestone acceptance omits completed work, deviations,
  remaining gaps, prior-plan assessment, replan rationale, or current evidence
- **THEN** FlowPilot SHALL reject the result mechanically
- **AND** the execution frontier SHALL remain at the current milestone.

### Requirement: Every major milestone rewrites the complete remaining route
Every top-level milestone acceptance SHALL submit one current remaining route
plan that begins from the audited current state and spans all remaining work to
the final user goal. The nearest next milestone SHALL be execution-ready;
farther milestones MAY be less detailed but SHALL remain explicit and
goal-connected.

#### Scenario: Current evidence changes the route
- **WHEN** completed work or deviations invalidate any part of the prior
  remaining plan
- **THEN** PM SHALL submit a revised complete remaining route
- **AND** FlowPilot SHALL NOT continue through the invalid old suffix.

#### Scenario: Prior remaining route is still fit
- **WHEN** PM concludes from the current audit that the prior remaining route is
  still the best route
- **THEN** PM SHALL resubmit the complete route with a fresh rationale
- **AND** the unchanged route SHALL still pass the full milestone gate.

#### Scenario: Remaining obligation is not owned
- **WHEN** a current unclosed hard obligation has no owner in the submitted
  remaining route
- **THEN** FlowPilot SHALL reject the plan
- **AND** SHALL NOT activate any part of it.

#### Scenario: Remaining gap lacks an owner node
- **WHEN** a non-empty audited remaining gap omits `owner_node_ids` or names a
  node outside the submitted remaining route
- **THEN** FlowPilot SHALL reject the result mechanically
- **AND** SHALL keep the current milestone gate unresolved.

### Requirement: Plan renewal is independently challenged before activation
FlowPilot SHALL stage top-level milestone acceptance and its remaining plan
without mutating the active route or frontier, then require current FlowGuard
review, PM absorption of that review, independent Reviewer challenge, and
system validation before one atomic commit.

#### Scenario: Reviewer has not passed
- **WHEN** the milestone audit and remaining plan are mechanically valid but the
  independent Reviewer has not passed the current staged result
- **THEN** the prior route and frontier SHALL remain active
- **AND** no next-milestone Worker packet SHALL be released.

#### Scenario: Reviewer finds an omitted or stale plan premise
- **WHEN** Reviewer blocks because completed evidence is weak, a deviation is
  hidden, a remaining gap is omitted, or the route no longer reaches the final
  goal
- **THEN** FlowPilot SHALL return to the current PM milestone result repair path
- **AND** SHALL NOT fall back to the old plan.

#### Scenario: All gate owners pass
- **WHEN** the current audit and remaining plan pass mechanical validation,
  FlowGuard, PM absorption, Reviewer, and system validation
- **THEN** FlowPilot SHALL atomically accept the milestone and renew the route
- **AND** only then MAY the frontier expose the next milestone.

### Requirement: Changed renewal replaces only unfinished work
When a reviewed remaining plan differs from the active unfinished route,
FlowPilot SHALL preserve accepted milestone history and evidence while
superseding or carrying forward only unfinished route nodes according to the
new plan.

#### Scenario: Remaining route changes
- **WHEN** a reviewed remaining plan differs from the current unfinished suffix
- **THEN** FlowPilot SHALL create one new active route version
- **AND** accepted nodes, accepted results, reviews, and validation evidence
  SHALL remain current history rather than being reset.

#### Scenario: Remaining route is exactly unchanged
- **WHEN** the canonical reviewed remaining plan equals the current unfinished
  suffix
- **THEN** FlowPilot SHALL record the new audit and review evidence
- **AND** SHALL NOT create a route version solely to restate identical route
  structure.

#### Scenario: Changed node reuses stale execution authority
- **WHEN** a revised route attempts to reactivate an old executed or superseded
  node as current authority
- **THEN** FlowPilot SHALL reject the plan
- **AND** SHALL require a fresh current node identity for the changed work.

### Requirement: Empty remaining plan is terminal-only
FlowPilot SHALL accept an empty remaining route only when the current milestone
audit declares no remaining goal gaps and every current hard obligation is
closed by current accepted evidence or an authorized disposition.

#### Scenario: Final milestone closes all obligations
- **WHEN** the final top-level milestone has current closure evidence
- **AND** the audit has no remaining gap and the remaining route has no nodes
- **THEN** FlowPilot MAY advance to the existing final-closure chain.

#### Scenario: Empty plan is premature
- **WHEN** any hard obligation or audited goal gap remains open
- **AND** PM submits an empty remaining route
- **THEN** FlowPilot SHALL reject the result
- **AND** SHALL keep the current milestone gate unresolved.

### Requirement: Hard-gate recovery resumes the same current obligation
Interrupted or resumed execution SHALL reconstruct the exact current
milestone-plan-renewal obligation and SHALL NOT infer continuation from the old
route, a historical audit, or a later route snapshot.

#### Scenario: Staged milestone gate is interrupted before review
- **WHEN** FlowPilot resumes with a current staged milestone result that lacks
  its required Reviewer result
- **THEN** FlowPilot SHALL re-expose the missing current review obligation
- **AND** SHALL leave the frontier and active route unchanged.

#### Scenario: Historical reviewed plan exists
- **WHEN** an older milestone has a reviewed plan but the current milestone gate
  is unresolved
- **THEN** FlowPilot SHALL NOT reuse the older review as current completion
  evidence.

### Requirement: Milestone renewal has one current mode
FlowPilot SHALL implement milestone-plan renewal as the sole current
top-level-milestone continuation path, without risk levels, optional
replanning, compatibility readers, fallback continuation, or experimental
old/new routing.

#### Scenario: Runtime encounters an old continuation marker
- **WHEN** a run contains a historical marker that previously allowed direct
  continuation through the original route
- **THEN** the marker SHALL NOT satisfy the current milestone gate
- **AND** FlowPilot SHALL require the current structured audit and remaining
  plan.
