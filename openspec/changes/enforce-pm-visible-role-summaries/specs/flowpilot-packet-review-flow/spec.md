## MODIFIED Requirements

### Requirement: PM packets include recent role-authored report summaries
FlowPilot SHALL include recent current-run role-authored report summaries in PM
packets through a structured `recent_role_report_summary` field without exposing
sealed result bodies.

#### Scenario: Ordinary PM packet receives prior role summaries
- **WHEN** runtime issues a PM-owned packet after accepted or semantically
  blocking non-PM role results exist in the current run
- **THEN** the PM packet body SHALL include `recent_role_report_summary` entries
  with role, packet id, result id, packet kind, and the role-authored summary
- **AND** the entries SHALL NOT include sealed packet body text or sealed result
  body text.

#### Scenario: Repair PM packet receives summary and body-read context
- **WHEN** runtime issues a PM repair-decision packet for a semantic blocker
- **THEN** the packet MAY include `recent_role_report_summary` for quick
  navigation and `authorized_result_reads` for formal body inspection
- **AND** PM SHALL NOT treat the summary as a substitute for any required
  result-body-open receipt.

### Requirement: Packets carry required result-read grants for downstream review
FlowPilot SHALL carry explicit `authorized_result_reads` grants into packets
whose recipient must inspect prior sealed role results or reports before
returning a decision, review, model, or repair output.

#### Scenario: Reviewer packet grants subject result read
- **WHEN** runtime issues a Reviewer packet for a subject result
- **THEN** the Reviewer packet SHALL include an authorized read grant for the
  subject result body
- **AND** the Reviewer must open that result before submitting the review when
  the grant is marked required.

#### Scenario: PM repair packet grants blocking review report read
- **WHEN** runtime issues a PM repair-decision packet because a Reviewer result
  blocked a subject packet
- **THEN** the PM packet SHALL include an authorized required read grant for the
  blocking Reviewer result body
- **AND** PM SHALL open the Reviewer report before submitting the repair
  decision.

#### Scenario: Fresh repair node inherits blocking report read
- **WHEN** PM chooses `repair_current_scope` and runtime opens a fresh repair
  node packet
- **THEN** the fresh repair packet SHALL inherit the unresolved blocking report
  read grant
- **AND** PM SHALL open that report before submitting the fresh repair node
  plan when the inherited grant is required.
