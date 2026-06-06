## MODIFIED Requirements

### Requirement: Formal role results carry PM-visible role-authored summaries
FlowPilot SHALL require formal non-PM role result bodies to include a
role-authored `pm_visible_summary` list before runtime accepts the result as
current-contract evidence.

#### Scenario: Role result with summary is eligible for normal processing
- **WHEN** a Worker, FlowGuard operator, or Reviewer submits a current strict
  JSON result body
- **AND** the body includes `pm_visible_summary` as a non-empty list of
  non-empty strings
- **THEN** runtime may process the result through the ordinary semantic pass or
  block path.

#### Scenario: Missing summary blocks the result contract
- **WHEN** a Worker, FlowGuard operator, or Reviewer submits an otherwise valid
  result body without a valid `pm_visible_summary`
- **THEN** runtime SHALL mark the result as a current result contract failure
- **AND** runtime SHALL reissue the same current packet family rather than
  treating runner-generated prose or sealed result text as the summary.

#### Scenario: Runner does not synthesize summary text
- **WHEN** runtime records or forwards PM-visible role report context
- **THEN** runtime SHALL use only the role-authored `pm_visible_summary` strings
- **AND** runtime SHALL NOT infer, summarize, or translate sealed role result
  body content into a substitute PM summary.

### Requirement: Downstream roles can open explicitly authorized result bodies
FlowPilot SHALL allow an assigned role to open a sealed result/report body only
when the current packet explicitly authorizes that result body for that role.

#### Scenario: Authorized role opens required result body
- **GIVEN** a packet body includes `authorized_result_reads[]` with a current
  `result_id`, `allowed_roles` containing the packet responsibility, and
  `required_before_submit=true`
- **WHEN** the assigned ACKed role runs `flowpilot_new.py open-result` for that
  result
- **THEN** runtime SHALL verify lease, packet, role, current result, and body
  hash
- **AND** runtime SHALL return the sealed result body only to that role
- **AND** runtime SHALL record a result-body-open receipt.

#### Scenario: Required result read blocks submission until opened
- **GIVEN** a packet has an `authorized_result_reads[]` row with
  `required_before_submit=true`
- **WHEN** the assigned role submits its packet result before opening that
  result body
- **THEN** runtime SHALL reject or mechanically block the submission
- **AND** runtime SHALL NOT treat unread prior report metadata or
  `recent_role_report_summary` as sufficient decision evidence.

#### Scenario: Controller cannot open result bodies
- **WHEN** Controller or a role not listed in `allowed_roles` attempts to open a
  sealed result body
- **THEN** runtime SHALL reject the open
- **AND** no sealed result body text SHALL be exposed.
