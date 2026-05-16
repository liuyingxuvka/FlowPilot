# controller-postcondition-blocker-routing Specification

## Purpose
TBD - created by archiving change fix-controller-postcondition-blocker-routing. Update Purpose after archive.
## Requirements
### Requirement: Missing Controller postconditions use mechanical reissue first
Router SHALL classify a `controller_action_receipt_missing_router_postcondition`
blocker as a mechanical control-plane reissue while its direct retry budget is
not exhausted.

#### Scenario: missing postcondition first issue
- **WHEN** Router writes a blocker from `controller_action_receipt_missing_router_postcondition` with no prior direct retry attempts
- **THEN** the blocker uses handling lane `control_plane_reissue`, policy row `mechanical_control_plane_reissue`, direct retry budget `2`, and a non-PM first handler.

#### Scenario: missing postcondition stays direct while budget remains
- **WHEN** the same missing-postcondition blocker family has used fewer direct retry attempts than its budget
- **THEN** Router SHALL continue routing it as a direct control-plane reissue instead of a PM repair decision.

### Requirement: Missing Controller postconditions escalate after bounded retry
Router SHALL escalate a repeated missing Controller postcondition to PM after
the mechanical direct retry budget is exhausted.

#### Scenario: retry budget exhausted
- **WHEN** a `controller_action_receipt_missing_router_postcondition` blocker reaches its direct retry budget
- **THEN** Router SHALL set the handling lane to `pm_repair_decision_required` and deliver the repair decision to PM.

### Requirement: Retry-budget metadata is internally consistent
Router SHALL record direct retry exhaustion consistently with the numeric retry
budget and attempts.

#### Scenario: zero direct retry budget
- **WHEN** a blocker has direct retry budget `0`
- **THEN** Router SHALL record that direct retry is exhausted and SHALL NOT present the blocker as having an available local retry.

#### Scenario: retry budget remains
- **WHEN** a mechanical blocker has used fewer attempts than its direct retry budget
- **THEN** Router SHALL record that direct retry is not exhausted.

### Requirement: Existing PM and fatal blockers keep their lanes
Router SHALL NOT reclassify semantic PM blockers, route-changing blockers,
self-interrogation blockers, or fatal protocol blockers into the mechanical
postcondition retry lane.

#### Scenario: unrelated semantic blocker
- **WHEN** Router writes an unrelated semantic control blocker
- **THEN** the blocker remains on its existing PM or fatal lane according to the blocker policy table.
