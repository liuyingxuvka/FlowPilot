## MODIFIED Requirements

### Requirement: Coverage matrix identifies system-level replay evidence

The synthetic agent coverage matrix SHALL distinguish local exception replay
from system-level replay stories.

#### Scenario: System replay row has recovery metadata

- **GIVEN** a coverage row declares `story_level: system`
- **WHEN** the coverage matrix is validated
- **THEN** the row SHALL have a non-empty `recovery_loop`
- **AND** it SHALL have at least two `story_steps`
- **AND** it SHALL declare `terminal_expectation`.

#### Scenario: Missing system metadata fails validation

- **GIVEN** a coverage row declares `story_level: system`
- **AND** it lacks recovery loop, story steps, or terminal expectation
- **WHEN** the matrix is validated
- **THEN** validation SHALL fail with a system replay metadata finding.

#### Scenario: System replay cannot claim live AI quality

- **GIVEN** a coverage row declares `story_level: system`
- **WHEN** the evidence boundary is validated
- **THEN** the row SHALL keep `live_completion_allowed` false
- **AND** it SHALL identify the control-plane recovery behavior it proves.
