# terminal-ledger Specification

## ADDED Requirements

### Requirement: Terminal replay includes FlowGuard coverage governance

Runtime SHALL issue a `flowguard-coverage-governance` terminal replay segment whenever high-standard FlowPilot closure requires FlowGuard terminal coverage.

#### Scenario: Reviewer terminal replay omits FlowGuard coverage governance
- **WHEN** runtime issues terminal segment targets
- **AND** `flowguard-coverage-governance` is required
- **THEN** a terminal replay result that omits the segment MUST be blocked.

### Requirement: Final projection uses current non-superseded artifacts

Final ledger and terminal replay SHALL close only against current accepted results and current final artifacts from the active route, not stale, superseded, repaired-before, or historical results.

#### Scenario: Superseded result is selected as final artifact
- **WHEN** the ledger/replay attempts to close final output using a stale or superseded result/artifact
- **THEN** final closure MUST remain blocked until PM projects a current artifact or records a valid waiver/stop.

### Requirement: Terminal quality gaps use existing supplemental repair path

Required terminal quality, final artifact hygiene, user-intent, or FlowGuard coverage gaps SHALL route through the existing terminal supplemental repair path and round cap.

#### Scenario: Terminal quality gap remains after replay
- **WHEN** Reviewer reports a required terminal blocker
- **THEN** PM MAY issue a supplemental repair contract using the existing path
- **AND** no more than three rounds may run for the same terminal gap before legal terminal disposition is required.
