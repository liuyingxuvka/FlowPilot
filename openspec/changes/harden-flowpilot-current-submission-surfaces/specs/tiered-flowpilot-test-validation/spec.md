## MODIFIED Requirements

### Requirement: Background regressions require completion artifacts
Background test or model regressions SHALL write stdout, stderr, combined
output, exit-code, and metadata artifacts. Progress output SHALL be liveness
evidence only, not completion evidence.

#### Scenario: Background progress is not reported as pass
- **GIVEN** a background regression has emitted progress lines
- **AND** the exit artifact is missing
- **WHEN** the result is reported
- **THEN** completion remains in progress or unknown
- **AND** pass/fail is not claimed.

#### Scenario: FlowPilot parent regressions use stable log names
- **WHEN** Meta or Capability parent regressions are run in the background
- **THEN** their artifacts MUST use the repository background log contract
  under `tmp/flowguard_background/`
- **AND** completion claims MUST inspect exit-code and metadata artifacts, not
  only stdout or progress lines.

