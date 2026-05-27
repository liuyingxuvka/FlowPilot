## ADDED Requirements

### Requirement: Daemon clears stale waits after internal evidence appears
The Router daemon SHALL reconcile stale Controller wait/projection rows when
authoritative Router-owned internal postcondition evidence exists.

#### Scenario: Old wait remains after capability sync evidence
- **WHEN** `capabilities/capability_sync.json` exists and validates
- **AND** `capability_evidence_synced` is recorded or can be reclaimed from the
  artifact
- **AND** an open or blocked Controller wait/reminder still names
  `capability_evidence_synced`
- **THEN** Router MUST mark that projection resolved from Router-owned evidence
- **AND** Router MUST NOT keep reporting that the Controller or reviewer is the
  missing actor for the already-satisfied postcondition
