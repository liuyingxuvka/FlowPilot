## ADDED Requirements

### Requirement: Closure Consumes Final Quality Blockers
FlowPilot closure SHALL consume unresolved final-quality evidence rows from the
final route-wide ledger, final requirement evidence matrix, and terminal
backward replay contract before allowing terminal return.

#### Scenario: Closed-looking record has final-quality blocker
- **WHEN** a route node appears accepted or waived
- **AND** its final matrix review, FlowGuard, validation, or terminal replay row
  is unresolved
- **THEN** closure MUST report the unresolved final-quality blocker
- **AND** Controller stop MUST remain unavailable.

#### Scenario: Historical evidence is present during closure
- **WHEN** closure sees historical or superseded evidence that does not belong
  to the active route
- **THEN** closure MUST keep active-route evidence unresolved
- **AND** the historical evidence MUST NOT be promoted into current closure
  proof.
