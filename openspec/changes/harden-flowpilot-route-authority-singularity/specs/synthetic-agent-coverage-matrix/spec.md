## ADDED Requirements

### Requirement: Fake AI wrong-path route-authority coverage
The synthetic agent coverage matrix SHALL include fake-AI cases for wrong route-authority submissions, repeated no-delta wrong-path retries, and corrected retries that follow the returned repair command.

#### Scenario: Repeated wrong-path package is non-live
- **WHEN** the fake AI repeats the same wrong project-manager route action after receiving a wrong-path rejection
- **THEN** the coverage matrix marks the row as non-live/no-delta rather than treating it as progress

#### Scenario: Corrected route action is live
- **WHEN** the fake AI changes its next packet to the current legal action named by the wrong-path repair feedback
- **THEN** the coverage matrix marks the corrected retry as returning to the main route authority path

### Requirement: Fake AI role-overreach coverage
The synthetic agent coverage matrix SHALL include role-overreach cases where Worker, Reviewer, and FlowGuard operator attempt route-control actions owned by the project manager or router.

#### Scenario: Reviewer cannot mutate route
- **WHEN** a fake Reviewer submits a route mutation or PM route decision
- **THEN** the matrix records that the attempt is rejected as wrong role and cannot advance the route

#### Scenario: FlowGuard cannot approve route action
- **WHEN** a fake FlowGuard operator submits approval, gate, or route mutation authority outside its model-report role
- **THEN** the matrix records rejection with the current owner and legal next action feedback
