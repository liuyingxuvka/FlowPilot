## ADDED Requirements

### Requirement: Executable bridge rows bind model cells to runtime evidence

FlowPilot SHALL maintain an executable matrix bridge that maps high-risk
model-local Cartesian cells to concrete fake AI packet bodies, public
Runtime/CLI entrypoints, expected outcomes, event-log evidence, convergence
rules, break-glass expectations, and freshness receipts.

#### Scenario: Bridge row is complete

- **WHEN** the executable bridge matrix is generated
- **THEN** every accepted bridge row MUST include `bridge_case_id`,
  `model_cell_id` or `coverage_shard_id`, `packet_family`, `fake_body_class`,
  `runtime_entrypoints`, `expected_outcome`, `event_log_evidence`,
  `convergence_rule`, `break_glass_expectation`, `evidence_command`, and
  `freshness_receipt_id`

#### Scenario: Missing runtime evidence blocks bridge pass

- **WHEN** a bridge row has model coverage but lacks fake-body, Runtime/CLI, or
  event-log evidence required by the row
- **THEN** the bridge checker MUST classify the row as model-only or incomplete
  rather than passed executable coverage

### Requirement: Bridge rows cover current known miss families

The executable bridge SHALL include required rows for the current known miss
families surfaced by fake project rehearsal and current-contract matrix review.

#### Scenario: Required miss family rows exist

- **WHEN** the executable bridge required-row inventory is checked
- **THEN** it MUST include rows for missing `current_evidence_refs`,
  moved/deleted/old stage fields, terminal `route_segment_replay`,
  `final_blockers`, terminal supplemental repair contract lineage, FlowGuard
  semantic recheck repair obligation consumption, old alias rejection, wrong
  role lease, missing ACK, stale node evidence, wrong FlowGuard target, dead
  lease, route mutation without frontier rewrite, slow reviewer progress,
  accepted packet reassignment, orphan runner summary, unsupported side command,
  and public CLI worker lifetime

#### Scenario: New break-glass incident creates bridge seed

- **WHEN** a real or rehearsal break-glass incident exposes a previously
  unmodeled same-class failure
- **THEN** the incident MUST produce a ModelMissReview seed and a new executable
  bridge row or explicit scoped-out decision before broad confidence is
  restored

### Requirement: Evidence levels remain distinct

FlowPilot SHALL distinguish model-only evidence, fake-body contract evidence,
Runtime/CLI replay evidence, long-chain convergence evidence, and parent
confidence evidence.

#### Scenario: Model-only evidence cannot satisfy executable confidence

- **WHEN** a coverage artifact cites only a model matrix result
- **THEN** it MUST NOT count as executable Runtime/CLI coverage or parent
  confidence for bridge rows

#### Scenario: Parent confidence requires current child evidence

- **WHEN** a parent coverage, install, topology, or final-confidence claim
  consumes bridge coverage
- **THEN** every required bridge child id MUST have current passing child
  evidence and a freshness receipt

### Requirement: Break-glass threshold is modeled precisely

FlowPilot SHALL forbid break-glass for known recoverable paths before the
configured no-progress threshold, and SHALL require Controller break-glass on
the fifth same-class no-progress repeat.

#### Scenario: Known recoverable path does not enter break-glass

- **WHEN** a bridge row injects a known bad package that has a legal reject,
  reissue, block, repair, redesign, or terminal-stop route
- **THEN** attempts one through four MUST remain in the normal control plane and
  MUST NOT enter break-glass

#### Scenario: Fifth no-progress repeat enters break-glass

- **WHEN** the same failure class repeats for the fifth time without repair
  delta, new evidence, or legal next-action progress
- **THEN** Controller break-glass MUST be the expected safety-fuse outcome
- **AND** the row MUST be reported separately from ordinary recovery success

### Requirement: Result freshness is required for broad claims

FlowPilot SHALL reject stale result artifacts as proof for executable matrix
coverage.

#### Scenario: Stale result artifact is rejected

- **WHEN** a bridge result file is older than its source model, fake body
  generator, test command, runtime entrypoint, or declared dependency
- **THEN** the bridge checker MUST classify the evidence as stale and prevent it
  from supporting broad confidence

#### Scenario: Fresh receipt supports reuse

- **WHEN** a previous result is reused
- **THEN** the reuse MUST include a current receipt binding command identity,
  source fingerprints, tested artifact fingerprints, dependency fingerprints,
  result status, and coverage scope
