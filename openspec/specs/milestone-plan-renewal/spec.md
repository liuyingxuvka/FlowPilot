# milestone-plan-renewal Specification

## Purpose

Defines the single current control loop that turns each completed major
milestone into a mandatory, independently challenged renewal of the complete
remaining plan before FlowPilot may continue toward the final user goal.
## Requirements
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
The PM-authored audit SHALL identify every completed top-level prefix row by
`node_id` and bind each remaining gap to one or more submitted remaining-plan
`owner_node_ids`. The runtime SHALL bind the current frozen final-goal
`contract_hash` and each completed row's exact current evidence set when it
stages the commit material; PM SHALL NOT copy those machine-owned fields into
semantic prose.

#### Scenario: Milestone audit is complete
- **WHEN** PM submits a top-level milestone acceptance
- **THEN** the audit SHALL explicitly include `completed`, `deviations`,
  `remaining`, `prior_plan_assessment`, and `replan_rationale`
- **AND** each completed claim SHALL include its current top-level `node_id`
  and semantic outcome
- **AND** the staged commit material SHALL bind the frozen final-goal contract
  hash and each row's complete runtime-issued evidence set
- **AND** PM-supplied `contract_hash` or completed-row `evidence_refs` SHALL be
  rejected as machine-owned fields.

#### Scenario: No deviation occurred
- **WHEN** current evidence reveals no material deviation from the prior plan
- **THEN** PM SHALL still submit an explicit empty `deviations` collection
- **AND** SHALL still assess the prior plan and justify the new submission.

#### Scenario: Audit omits a required surface
- **WHEN** a top-level milestone acceptance omits completed work, deviations,
  remaining gaps, prior-plan assessment, or replan rationale
- **THEN** FlowPilot SHALL reject the result mechanically
- **AND** the execution frontier SHALL remain at the current milestone.

### Requirement: Renewal evidence reads stay bounded to the current delta
The PM renewal packet SHALL authorize the current milestone evidence and, when
present, the immediately previous accepted milestone audit result. It SHALL NOT
reopen every historical evidence body merely to restate the accepted prefix;
the runtime-owned accepted-prefix projection remains the machine authority.

#### Scenario: A later milestone opens its renewal packet
- **WHEN** one or more earlier top-level milestones have already completed
- **THEN** PM SHALL receive the current milestone evidence plus the immediately
  previous accepted milestone audit result
- **AND** older completed evidence bodies SHALL remain represented by the
  runtime-owned accepted-prefix projection rather than being reopened.

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

### Requirement: Renewal bindings are current and exhaustive
The renewal contract SHALL bind machine-owned route, contract, evidence, and
obligation identities from the current runtime projection while requiring PM
to provide the semantic audit and complete route.

#### Scenario: Runtime supplies concrete remaining owners
- **WHEN** the current PM packet contains concrete remaining owner node ids
- **THEN** its minimal valid shape SHALL use the same node identities
- **AND** the shape SHALL not contain a fixed example owner that the current
  validator would reject.

#### Scenario: A non-route gap remains open
- **WHEN** unresolved artifact hygiene, open-resource, residual-risk, or
  legacy-evidence gaps remain in the current obligation projection
- **THEN** the renewal SHALL require those gaps to be represented by current
  route owners or an explicit current disposition
- **AND** an empty or otherwise unowned route SHALL be rejected.

#### Scenario: A nested helper node has no distinct goal gap
- **WHEN** a valid remaining route contains an implementation child whose work
  is covered by its parent milestone gap
- **THEN** the renewal SHALL permit the child to remain in the route
- **AND** SHALL not require PM to invent a separate artificial user-goal gap
  solely for that child.

#### Scenario: PM cites evidence without reading it
- **WHEN** PM submits a milestone audit that cites sealed result ids but has not
  consumed the required authorized result reads
- **THEN** the renewal SHALL remain blocked
- **AND** a summary or evidence id alone SHALL not count as formal evidence.

### Requirement: Changed-suffix renewal closes the old lifecycle
Changed-suffix activation SHALL reuse the current route-mutation lifecycle for
quarantine, evidence invalidation, version activation, and repair-blocker
retirement.

#### Scenario: Replaced suffix has an open repair blocker
- **WHEN** a changed renewal replaces an unfinished suffix containing an open
  repair blocker
- **THEN** the blocker SHALL be explicitly superseded or retired with the
  mutation
- **AND** it SHALL not remain an active blocker at terminal closure.

### Requirement: Top-level milestone quality remains review-owned
The runtime SHALL use topology alone to identify the hard gate, while Reviewer
quality checks SHALL challenge unreasonable top-level granularity.

#### Scenario: One top-level parent swallows the whole project
- **WHEN** the initial route puts all meaningful work below one non-terminal
  top-level parent
- **THEN** Reviewer SHALL be able to block the route as an unsuitable global
  milestone decomposition
- **AND** FlowPilot SHALL not add a risk tier or runtime scoring field.

### Requirement: Structural PPA tests remain distinct from live closure evidence
The existing TestMesh/MTA execution tiers SHALL keep the exact PPA
maintenance unit in the all-tier supplement. Contract-shape assertions MAY
use an explicit repository-relative proof artifact marked
`structural_shape_only` for the contract-matrix paths, but that artifact SHALL
not be accepted as live matrix evidence. The closure runner SHALL remain the
sole owner of live PPA evidence and SHALL consume current matrix and MTA
results after their producer stages complete.

#### Scenario: Fresh source snapshot has no prior current matrix result
- **WHEN** a new source snapshot starts the all-tier validation
- **AND** the PPA contract-shape unit tests inspect a contract-matrix path
- **THEN** those tests SHALL use only their explicit structural proof projection
- **AND** the all-tier bundle SHALL still include the exact PPA unit owner.

#### Scenario: Closure runner sees stale or failed live evidence
- **WHEN** the current matrix or MTA result is missing, stale, or failed at
  closure
- **THEN** the live PPA runner SHALL fail closed
- **AND** the structural unit proof SHALL not be promoted to current runtime
  evidence.

### Requirement: Frozen validation fails closed when an execution owner disappears
The bounded background supervisor SHALL track each launched validation owner's
exact process identity and immutable terminal receipt. A child that exits or
exceeds its bounded deadline without publishing that receipt SHALL make the
supervisor terminally fail. A stale `running` slot, PID, progress line, or empty
stream SHALL NOT count as completion or reusable evidence. Any remaining exact
validation processes SHALL be cleaned up, and unconfirmed descendant-zero
cleanup SHALL remain visibly blocked.

#### Scenario: A validation child disappears before terminal publication
- **WHEN** an all-tier child process is no longer live
- **AND** its immutable terminal exit artifact is absent after the bounded
  publication grace window
- **THEN** the supervisor SHALL publish a non-success terminal result
- **AND** it SHALL NOT wait forever or promote prior progress as evidence
- **AND** cleanup-unconfirmed status SHALL block every release claim.

### Requirement: One frozen baseline remains selectively reusable
The current impact planner and final verifier SHALL use the same strict
FlowGuard reuse-ticket validity rule. An unchanged owner SHALL be reusable only
when its immutable producer receipt is a terminal pass with confirmed cleanup,
its producer and current execution owners match, and its complete verifier
fingerprints match. A rejected ticket SHALL be classified before execution as
an affected owner and SHALL NOT trigger an automatic full-suite fallback.

#### Scenario: Exact unchanged owner follows a successful 228-owner baseline
- **WHEN** an earlier frozen baseline contains a current terminal proof for the
  same execution owner and all verifier fingerprints still match
- **THEN** the impact plan SHALL reuse that owner without executing it again
- **AND** final verification SHALL accept the same ticket with the same rule.

#### Scenario: Reuse proof is incomplete or its identity changed
- **WHEN** the producer receipt, terminal status, cleanup proof, execution
  owner, or any required verifier fingerprint is missing or changed
- **THEN** the planner SHALL select only that owner and its affected dependency
  closure for execution
- **AND** it SHALL NOT convert the condition into a run-all fallback.

### Requirement: All-tier execution checks contract authority before launch
A real `all`-tier execution SHALL check FlowPilot's current SkillGuard contract
and depth authority before the 228 command owners are built or launched. A
stale or blocked contract SHALL stop in preflight. Dry-run planning and
read-only receipt verification SHALL remain non-executing.

#### Scenario: SkillGuard contract changed after the prior baseline
- **WHEN** a caller requests a real `all`-tier launch and the current contract
  check does not pass
- **THEN** FlowPilot SHALL return a visible preflight failure before launching
  any validation owner.

### Requirement: Runtime evidence consumers bind successful producer owners
Runtime-generated reports and receipts SHALL remain evidence outputs rather
than source-authority inputs. A consumer that reads such an output SHALL
declare the exact producer owner and SHALL start only after that producer has
published a current successful terminal receipt. A failed, blocked, missing,
or unresolved producer SHALL keep the consumer unlaunched and the parent
validation non-successful.

#### Scenario: Producer refreshes a result during one frozen validation
- **WHEN** a producer writes its current runtime evidence result after the
  all-tier impact plan is frozen
- **THEN** the result file SHALL NOT make the consumer's source identity stale
- **AND** the consumer SHALL bind the producer-owner dependency and read the
  newly produced result only after producer success.

#### Scenario: Required evidence producer fails
- **WHEN** a declared runtime evidence producer is failed, blocked, missing, or
  unresolved
- **THEN** its consumer SHALL NOT launch against a historical result file
- **AND** the parent validation SHALL remain visibly non-successful.

