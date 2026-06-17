## ADDED Requirements

### Requirement: Terminal Ledger Includes Acceptance Item Closure
FlowPilot terminal final ledger construction SHALL include an acceptance item
closure table for every active item in the current registry and MUST keep
unclosed, stale, low-quality, orphan, or unauthorized-waiver items unresolved.

#### Scenario: Final ledger sees unresolved acceptance item
- **WHEN** an active acceptance item is missing current high-quality closure
  evidence
- **THEN** the terminal ledger MUST include an unresolved item row
- **AND** final closure MUST remain blocked.

#### Scenario: Superseded item has authority
- **WHEN** an acceptance item is no longer active because of route mutation
- **THEN** the terminal ledger MUST cite the supersession or waiver authority
- **AND** the item MUST NOT silently disappear from the final trace.
