## ADDED Requirements

### Requirement: Research batch joins reconcile through Router durable wait evidence
Router durable wait reconciliation SHALL fold a joined `research` packet batch
into the existing `worker_research_report_returned` event before selecting the
next action or wait reminder.

#### Scenario: Research result envelopes already exist
- **WHEN** the active `research` packet batch has result envelopes for every
  blocking member
- **AND** the research packet has been relayed and the worker research report
  card has been delivered
- **THEN** Router records `worker_research_report_returned` from the durable
  result envelope metadata
- **AND** the next action MAY use the existing `relay_research_result_to_pm`
  path.

#### Scenario: Research batch is partial
- **WHEN** only some research result envelopes exist
- **THEN** Router records returned and missing batch members
- **AND** keeps waiting only for the missing research roles.

#### Scenario: Research wait is already satisfied
- **WHEN** a pending research wait still exists after all research result
  envelopes are present and valid
- **THEN** Router reconciles the wait as satisfied before materializing a new
  wait-target reminder.

### Requirement: Research reconciliation preserves sealed body boundaries
Router SHALL reconcile research result completion using only envelope paths,
hashes, packet ids, batch ids, role metadata, and next-recipient metadata.

#### Scenario: Result bodies are sealed
- **WHEN** research result bodies exist beside valid result envelopes
- **THEN** Router MUST NOT read or summarize those bodies during durable wait
  reconciliation
- **AND** PM body access remains deferred until the PM relay path.
