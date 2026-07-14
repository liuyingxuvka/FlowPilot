# flowguard-full-coverage-findings Specification

## Purpose
TBD - created by archiving change close-flowguard-full-coverage-findings. Update Purpose after archive.
## Requirements
### Requirement: Split Facade Source Audits Resolve Owner Modules

FlowGuard source audits SHALL resolve behavior-bearing helpers and data tables
from the owner modules exported through a unsupported historical facade.

#### Scenario: helper moved out of router facade

- **WHEN** the small router facade imports and exports a helper from an owner
  module
- **THEN** the source audit SHALL treat that helper as present.

#### Scenario: external event table moved out of router facade

- **WHEN** `EXTERNAL_EVENTS` is exported from a protocol owner module
- **THEN** the expected-event audit SHALL use that table instead of reporting
  it as missing from the facade.

### Requirement: Metadata-Only Startup Intake Projection Recognizes Controller Relay

The daemon reconciliation live projection SHALL recognize startup user intake as
controller-relayed when the packet ledger records a controller relay to the
project manager and the packet status shows recipient-opened or returned
evidence.

#### Scenario: controller-relayed intake is opened by recipient

- **WHEN** the user-intake packet holder is `project_manager`
- **AND** controller relay metadata records delivery to `project_manager`
- **AND** the packet status is `packet-body-opened-by-recipient` or
  `result-body-opened-by-recipient`
- **THEN** the live projection SHALL not report
  `startup_intake_release_user_intake_not_controller_relayed`.

### Requirement: Inventory Distinguishes Artifact Choices From Skipped Evidence

The full coverage inventory SHALL not classify an otherwise parsed runner as
skipped evidence solely because a read-only sweep did not provide a default
result-file output path.

#### Scenario: runner emitted parseable stdout without json-out

- **WHEN** a runner is parsed successfully from current stdout
- **AND** the only skipped check is `default_results_file`
- **THEN** the inventory SHALL not classify that runner as
  `skipped_or_scoped_evidence`.

