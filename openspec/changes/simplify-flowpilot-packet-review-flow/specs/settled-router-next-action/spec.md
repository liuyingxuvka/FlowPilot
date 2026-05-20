## ADDED Requirements

### Requirement: Result relay next action follows the result recipient
Router SHALL derive result-relay next-action text from the result envelope's expected recipient. PM-bound results SHALL direct Controller to PM disposition; Reviewer-bound results SHALL direct Controller to Reviewer delivery.

#### Scenario: PM-bound result produces PM disposition notice
- **WHEN** a PM-issued packet result has `next_recipient: project_manager`
- **THEN** Router SHALL expose a Controller-visible notice equivalent to `deliver_result_to_pm_for_disposition`
- **AND** Router SHALL NOT expose that result as a direct Reviewer review action.

#### Scenario: Reviewer-bound result keeps Reviewer delivery notice
- **WHEN** a result contract explicitly has `next_recipient: human_like_reviewer`
- **THEN** Router SHALL expose a Reviewer delivery notice only after packet-ledger and recipient checks pass.
