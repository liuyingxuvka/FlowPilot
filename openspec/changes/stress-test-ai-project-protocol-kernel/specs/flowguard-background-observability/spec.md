## ADDED Requirements

### Requirement: Protocol stress evidence consumes final background artifacts
FlowPilot protocol stress validation SHALL count heavyweight background model
regressions only when final stdout, stderr, combined output, exit, and metadata
artifacts have been inspected and recorded as current.

#### Scenario: Background regression is still running
- **WHEN** the protocol stress evidence matrix sees progress output without a
  successful exit artifact and metadata completion status
- **THEN** the background child row is classified as progress-only or
  incomplete and cannot satisfy parent stress confidence.

#### Scenario: Background regression completed successfully
- **WHEN** the protocol stress evidence matrix sees exit code `0`, metadata
  status `passed`, current timestamps, and no invalid proof reuse
- **THEN** the background child row can count as current pass evidence.
