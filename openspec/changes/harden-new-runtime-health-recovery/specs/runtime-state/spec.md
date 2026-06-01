## MODIFIED Requirements

### Requirement: Terminal Current Pointer Status

The current-run pointer SHALL derive terminal status from terminal return
authority and closure state instead of showing stale lifecycle-only state.

#### Scenario: Terminal return updates current pointer status

- **GIVEN** closure is complete and final preflight allows terminal return
- **WHEN** the run shell refreshes `.flowpilot/current.json`
- **THEN** the pointer shows terminal completion status
- **AND** it preserves the ledger path and run root authority fields
