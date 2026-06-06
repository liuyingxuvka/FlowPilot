## MODIFIED Requirements

### Requirement: PM repair packets preserve concrete role repair guidance
FlowPilot SHALL preserve structured concrete repair guidance from blocking role
results when creating PM repair-decision packets.

#### Scenario: Reviewer required repair reaches PM
- **WHEN** a Reviewer blocks a result and includes
  `blocking_findings[].required_repair`
- **THEN** runtime SHALL carry that required repair into the semantic blocker
  and PM repair-decision packet as PM-facing repair guidance
- **AND** PM SHALL NOT receive only a generic phrase such as "reviewer reported
  block" when concrete structured guidance exists.

#### Scenario: Generic repair guidance remains only when no concrete guidance exists
- **WHEN** a blocking result has no structured required repair and no
  role-authored PM-visible summary
- **THEN** runtime may use the existing generic blocker recommendation only as
  generic repair guidance
- **AND** the missing summary contract SHALL still be enforced for formal
  non-PM role results.

### Requirement: PM repair decisions are based on opened blocking reports
FlowPilot SHALL require PM repair-decision packets to carry and enforce
authorized reads for the blocking role result/report that caused the repair
when formal body inspection is required.

#### Scenario: Reviewer block reaches PM as readable report
- **WHEN** a Reviewer blocks a result
- **THEN** runtime SHALL create a PM repair-decision packet that authorizes PM
  to open the blocking Reviewer result body when that body is needed for the
  repair decision
- **AND** the packet SHALL require that open before PM can submit the repair
  decision when `required_before_submit=true`.

#### Scenario: Summary does not replace body-read authority
- **WHEN** the PM repair packet carries `recent_role_report_summary`
- **THEN** PM may use the summary to locate the relevant issue quickly
- **AND** PM SHALL still open any required authorized blocking report before
  making the formal repair decision.

#### Scenario: Stop or waiver does not require fresh repair inheritance
- **WHEN** PM chooses a terminal stop or authorized waiver path
- **THEN** runtime SHALL record the decision and SHALL NOT open a fresh repair
  node only to satisfy inherited report reads.
