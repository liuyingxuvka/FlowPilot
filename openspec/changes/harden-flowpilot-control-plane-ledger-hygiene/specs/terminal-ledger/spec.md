## ADDED Requirements

### Requirement: Terminal return consumes whole-ledger hygiene
FlowPilot SHALL run a whole-ledger hygiene gate before final closure and
terminal return, separate from current-target scheduling filters.

#### Scenario: Stale active blocker remains in registry
- **WHEN** an active blocker remains in the ledger registry even though its
  route node or packet is no longer current-target-effective
- **THEN** final closure and terminal return MUST block
- **AND** runtime MUST NOT filter it out solely through
  `_blocker_current_effective`

#### Scenario: Dirty accepted pointer remains before terminal return
- **WHEN** any packet in the closure evidence surface has an accepted pointer
  violation
- **THEN** final closure and terminal return MUST block
- **AND** runtime MUST report the dirty pointer rather than silently ignoring
  the packet
