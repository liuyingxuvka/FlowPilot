## ADDED Requirements

### Requirement: New runtime terminal lifecycle is persisted consistently
The runtime ledger SHALL persist stop/cancel lifecycle state, lease closure,
packet settlement, lifecycle guard, foreground duty, and current-run pointer
updates as one terminal lifecycle transition.

#### Scenario: Terminal lifecycle refresh updates public status
- **WHEN** a new-runtime stop or cancel command succeeds
- **THEN** subsequent `status`, `patrol`, and `final-preflight` commands MUST
  report the same terminal lifecycle state
- **AND** active lease count MUST be zero
- **AND** no stopped or cancelled packet MUST be reassigned by normal
  `lease-agent` flow.

### Requirement: Host liveness evidence is ledger-backed and timestamped
The runtime ledger SHALL store host-liveness reports with status, timestamp,
lease id, packet id, and source while keeping sealed packet/result bodies
invisible.

#### Scenario: Host liveness record is metadata-only
- **WHEN** `flowpilot_new.py host-liveness` records a host status
- **THEN** the active lease MUST include the latest liveness status and checked
  timestamp
- **AND** a bounded history entry MUST be appended
- **AND** the record MUST NOT include sealed packet or result body text.

### Requirement: Orphan evidence records are current-run metadata
The runtime ledger SHALL persist orphan evidence findings as current-run
metadata keyed by packet id and evidence root.

#### Scenario: Orphan evidence finding is stable across status reads
- **WHEN** lifecycle guard detects orphan mechanical evidence for a packet
- **THEN** the ledger MUST retain an orphan evidence record for that packet
- **AND** repeated `status` or `patrol` reads MUST not duplicate records or
  change packet completion state.
