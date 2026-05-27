# flowguard-exposed-issue-repair Specification

## Purpose
TBD - created by archiving change repair-flowguard-exposed-issues. Update Purpose after archive.
## Requirements
### Requirement: Compatibility Facade JSON Capability Is Discovered

The coverage sweep SHALL discover compact JSON support from a compatibility
facade's implementation module when the facade itself delegates to `_impl`.

#### Scenario: facade delegates to JSON-capable implementation

- **WHEN** a `run_*checks.py` facade imports `<name>_runner_impl as _impl`
- **AND** the implementation declares `--json`
- **THEN** the sweep SHALL invoke the facade with `--json`.

### Requirement: Read-Only Sweep Avoids Result Refresh When Supported

The coverage sweep SHALL preserve read-only behavior for delegated runners
that support a no-write flag.

#### Scenario: implementation supports no-write-results

- **WHEN** a delegated implementation declares `--no-write-results`
- **THEN** the sweep SHALL pass `--no-write-results` during read-only execution.

### Requirement: Process Liveness Is Parseable Evidence

The coverage inventory SHALL not classify `flowpilot_process_liveness` as an
unparsed runner when the delegated runner can emit compact JSON.

#### Scenario: process liveness runner is swept

- **WHEN** the coverage sweep runs `run_flowpilot_process_liveness_checks.py`
- **THEN** the inventory record for `flowpilot_process_liveness` SHALL be
  parsed and SHALL not include `runner_unparsed_or_unavailable`.
