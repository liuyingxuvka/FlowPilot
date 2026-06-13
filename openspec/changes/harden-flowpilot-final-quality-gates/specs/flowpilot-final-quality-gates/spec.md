## ADDED Requirements

### Requirement: Final Evidence Rows Require Current Passing Records
FlowPilot final route-wide ledgers and final requirement evidence matrices SHALL
count a review, FlowGuard order, or validation evidence id as covered only when
the referenced record exists, belongs to the current route or current source
generation as applicable, has a passing decision/status, and has no current
blockers.

#### Scenario: Blocked review id remains unresolved
- **WHEN** a current route node references a Reviewer record whose decision is
  `block` or whose blocker list is non-empty
- **THEN** the final requirement evidence matrix MUST mark that node's review
  row as unresolved
- **AND** final closure MUST NOT count that review id as independent review
  proof.

#### Scenario: Stale FlowGuard id remains unresolved
- **WHEN** a current route node references a FlowGuard work order whose proof is
  stale, progress-only, skipped, failed, missing its proof artifact, or from an
  old source generation
- **THEN** the final requirement evidence matrix MUST mark that node's
  FlowGuard row as unresolved
- **AND** final closure MUST NOT count that work order as FlowGuard proof.

#### Scenario: Failed validation id remains unresolved
- **WHEN** a current route node references validation evidence whose status is
  not `passed`, whose source generation is stale, or whose blockers list is
  non-empty
- **THEN** the final requirement evidence matrix MUST mark that node's
  validation row as unresolved
- **AND** final closure MUST NOT count that validation id as validation proof.

### Requirement: Final Gates Ignore Historical Route Evidence
FlowPilot SHALL build final ledger, final requirement matrix, and terminal
replay targets from the active route only. Evidence attached only to old route
versions, superseded route nodes, or historical artifacts MUST NOT close a
current-route requirement.

#### Scenario: Old route node has passing evidence
- **WHEN** a previous route version contains accepted review, FlowGuard, and
  validation evidence
- **AND** the active route does not contain equivalent current passing evidence
- **THEN** final route-wide ledger and final requirement evidence matrix MUST
  keep the active route rows unresolved.

### Requirement: Terminal Replay Covers Runtime-Issued Targets
FlowPilot terminal backward replay SHALL pass only when the Reviewer result
covers every segment target issued by the runtime for the active route and no
unexpected or duplicate segment id is present.

#### Scenario: Terminal replay omits a segment
- **WHEN** runtime issues terminal replay segment targets for the root contract
  and active route nodes
- **AND** Reviewer submits a terminal replay result missing one target segment
- **THEN** the terminal replay result MUST be mechanically blocked
- **AND** final closure MUST remain unavailable.

#### Scenario: Terminal replay includes unexpected segment
- **WHEN** Reviewer submits a terminal replay result containing a segment id not
  issued by runtime for the active route
- **THEN** the terminal replay result MUST be mechanically blocked
- **AND** the unexpected segment MUST NOT be treated as supplemental coverage.
