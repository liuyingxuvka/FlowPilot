## MODIFIED Requirements

### Requirement: Daemon saves preserve newer durable evidence

The persistent Router daemon SHALL save `router_state` only after checking whether the file or durable evidence changed since the daemon snapshot.

#### Scenario: Daemon detects stale snapshot before save
- **WHEN** daemon processing started from a prior state version
- **AND** foreground Controller receipt or event handling wrote a newer state version
- **THEN** daemon save MUST reload current state, merge durable facts, and retry or write the merged result
- **AND** the daemon MUST NOT discard the newer foreground receipt/event/history evidence
