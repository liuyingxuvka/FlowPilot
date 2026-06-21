## ADDED Requirements

### Requirement: Role replacement commit rejects forbidden same-agent reuse

FlowPilot SHALL enforce reviewer and role-replacement identity constraints at
the runtime lease commit point, not only at the role-resolution planning point.

#### Scenario: Replacement resolves but host returns same agent
- **WHEN** role resolution requires `create_new_role` because the prior agent is
  forbidden for the current packet
- **AND** the lease request provides the same effective agent id as the
  forbidden prior agent
- **THEN** runtime MUST reject the lease commit with a current-contract error
  naming the replacement reason and forbidden prior agent id
- **AND** runtime MUST NOT record the role as replaced or current

#### Scenario: Replacement uses a different agent
- **WHEN** role resolution requires `create_new_role`
- **AND** the lease request provides an effective agent id outside the forbidden
  prior-agent set
- **THEN** runtime MAY commit the lease through the existing role-assignment
  path

### Requirement: System validation requires an accepted independent review

FlowPilot SHALL treat review metadata as part of system validation. A subject
result is not system-validated merely because it has a review id.

#### Scenario: Review row contains self-review blocker
- **WHEN** a review record for the subject result has `decision=block`,
  nonempty blockers, or an independence blocker such as `self_review`
- **THEN** system validation MUST fail with a blocker naming the rejected review
  condition
- **AND** terminal closure MUST NOT treat the subject result as accepted

#### Scenario: Accepted review validates result
- **WHEN** the review record is current, accepted, independent from the
  producer, has direct evidence, and has no blockers
- **THEN** system validation MAY count the review as satisfying the review gate

### Requirement: Runtime feedback names exact current-contract repair

FlowPilot SHALL make mechanical contract feedback actionable for the current
packet/result surface.

#### Scenario: Required field or artifact is missing
- **WHEN** runtime rejects a packet/result because a required field, formal
  artifact, body file, or projection row is missing
- **THEN** the feedback MUST name the required path or artifact id, the observed
  bad value or absence, and the minimal current-contract repair expected from
  the responsible role

#### Scenario: Unsupported old shape is submitted
- **WHEN** a result uses an unsupported old field, legacy wrapper, alias, or
  prose substitute
- **THEN** runtime MUST reject it instead of translating it into the current
  shape
