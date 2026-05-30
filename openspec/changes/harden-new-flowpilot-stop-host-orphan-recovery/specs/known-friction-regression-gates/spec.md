## ADDED Requirements

### Requirement: Stop-host-orphan misses are required regression gates
FlowPilot regression gates SHALL include same-class failures for nonterminal
stop without terminal fence, host-liveness failure hidden by stale progress,
and orphan mechanical evidence without formal result submission.

#### Scenario: Stop without lifecycle fence is a known bad case
- **WHEN** a model, rehearsal, or runtime audit marks a user stop as foreground
  exit while the new-run ledger remains running
- **THEN** the known-friction gate MUST fail.

#### Scenario: Stale progress hides host loss
- **WHEN** a lease has old progress but the latest host status is missing,
  cancelled, or timeout-unknown
- **THEN** the known-friction gate MUST fail if the guard remains in normal
  wait patrol.

#### Scenario: Orphan evidence is accepted or ignored
- **WHEN** runner evidence completes without a formal result envelope
- **THEN** the known-friction gate MUST fail if the runtime either accepts the
  packet from evidence alone or keeps waiting without a recovery duty.
