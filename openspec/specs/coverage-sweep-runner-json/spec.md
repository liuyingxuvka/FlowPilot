# coverage-sweep-runner-json Specification

## Purpose
TBD - created by archiving change repair-coverage-sweep-runner-json. Update Purpose after archive.
## Requirements
### Requirement: Coverage sweep requests JSON stdout from JSON-capable runners

The FlowGuard coverage sweep SHALL pass `--json` when executing a read-only
runner that advertises a JSON stdout option.

#### Scenario: Runner supports both JSON stdout and JSON file output

- **WHEN** a read-only runner supports both `--json` and `--json-out`
- **THEN** the coverage sweep MUST execute it with `--json`
- **AND** the coverage sweep MUST NOT pass `--json-out`
- **AND** the runner's stdout MUST be parsed as the coverage payload.

### Requirement: Coverage sweep remains read-only

The FlowGuard coverage sweep SHALL NOT refresh persisted result files when it
executes runners for status collection.

#### Scenario: JSON-capable runner is executed during sweep

- **WHEN** the coverage sweep runs a JSON-capable runner
- **THEN** the command MUST request JSON stdout only
- **AND** no JSON output path MUST be supplied by the sweep.
