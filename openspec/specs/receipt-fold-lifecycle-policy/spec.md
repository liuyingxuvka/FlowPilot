# receipt-fold-lifecycle-policy Specification

## Purpose
TBD - created by archiving change prune-receipt-fold-lifecycle-policy. Update Purpose after archive.
## Requirements
### Requirement: Receipt fold lifecycle writeback uses one target policy

FlowPilot SHALL derive packet/result receipt lifecycle target fields from one
internal policy before applying lifecycle writes.

#### Scenario: Packet dispatch maps to packet lifecycle status

- **WHEN** a registered Controller receipt fold has kind `packet_dispatch`
- **THEN** the lifecycle policy MUST select `packet_relayed` as the record,
  timestamp, batch, and officer lifecycle status.

#### Scenario: Result relay maps to recipient-specific lifecycle status

- **WHEN** a registered Controller receipt fold has kind `result_relay`
- **THEN** the lifecycle policy MUST select the result-relay status for the
  intended recipient without changing packet/result evidence validation.

#### Scenario: Unsupported lifecycle kind is not folded by policy

- **WHEN** a receipt fold kind has no packet or result lifecycle writeback
- **THEN** the policy MUST return no lifecycle target and the caller MUST
  preserve the existing no-op or dedicated branch behavior.

### Requirement: Branch pruning preserves receipt evidence authority

FlowPilot SHALL keep packet/result evidence validation and sealed-body
visibility boundaries unchanged while pruning lifecycle writeback branches.

#### Scenario: Evidence validation remains separate from lifecycle writeback

- **WHEN** a Controller receipt fold evaluates packet or result evidence
- **THEN** packet and result validators MUST remain distinct and lifecycle
  writeback MUST run only after all selected records are satisfied.

#### Scenario: Public receipt fold surface remains stable

- **WHEN** lifecycle writeback is refactored
- **THEN** the receipt fold registry, exported helper names, action types,
  Router flags, and returned fold summary fields MUST remain compatible.
