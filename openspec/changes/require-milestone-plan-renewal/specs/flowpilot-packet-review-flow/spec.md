## ADDED Requirements

### Requirement: Major milestone disposition is reviewed before frontier advance
FlowPilot SHALL treat the current top-level milestone PM disposition, milestone
audit, and complete remaining route as one staged review subject. It SHALL NOT
record final milestone acceptance or advance the execution frontier until the
existing independent challenge and validation chain passes.

#### Scenario: PM submits a valid milestone renewal
- **WHEN** a top-level milestone PM disposition is mechanically valid
- **THEN** Router SHALL stage its route effect and release the current
  FlowGuard and Reviewer obligations
- **AND** SHALL keep the current route and frontier unchanged.

#### Scenario: Independent review blocks the renewal
- **WHEN** Reviewer rejects the evidence accounting, deviation analysis,
  remaining-gap coverage, route depth, or final-goal continuity
- **THEN** the PM disposition SHALL remain unapplied
- **AND** Router SHALL NOT release a dependent next-node packet.

#### Scenario: Independent review passes the renewal
- **WHEN** the staged milestone renewal has current passing FlowGuard,
  PM-absorption, Reviewer, and system-validation evidence
- **THEN** Router SHALL commit milestone acceptance and the reviewed remaining
  route as one outcome.

### Requirement: Reviewer challenges current evidence and future route together
Reviewer SHALL inspect the current milestone audit and complete remaining plan
as one continuity claim: the completed evidence must support the current state,
the deviations must be honest, every remaining hard gap must retain an owner,
and the route must still reach the accepted final goal. The PM, FlowGuard, and
Reviewer packet contexts SHALL carry the same frozen final-goal contract
projection; checker identities SHALL not self-review any required authorized
input they produced.

#### Scenario: Plan is unchanged but freshly grounded
- **WHEN** the canonical route is unchanged
- **AND** the audit demonstrates that current evidence leaves its premises,
  ordering, coverage, and final-goal connection valid
- **THEN** Reviewer MAY pass without demanding artificial structural change.

#### Scenario: Plan is unchanged without current justification
- **WHEN** PM merely repeats the prior route without reconciling current
  completed work, deviations, and remaining gaps
- **THEN** Reviewer SHALL block the milestone renewal.

#### Scenario: Near work remains vague
- **WHEN** the first remaining milestone lacks an executable outcome,
  acceptance boundary, dependency boundary, or current proof path
- **THEN** Reviewer SHALL block even if distant route nodes name the final goal.
