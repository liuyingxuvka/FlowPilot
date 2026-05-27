## ADDED Requirements

### Requirement: Material Progress Singleton Evidence Is Generation-Scoped
FlowPilot SHALL include material progress state in singleton evidence using the active material batch and current material generation rather than run-wide progress booleans alone.

#### Scenario: Stale progress flag cannot own new generation
- **WHEN** a stale run-wide material progress flag is true for an older material generation
- **AND** the active material generation still has pending packet, result, or PM disposition work
- **THEN** singleton evidence reports the older flag as stale and preserves the active generation obligation

#### Scenario: Reissue creates new material authority
- **WHEN** material repair reissues work into a new generation
- **THEN** the old generation's progress, results, and PM disposition are either superseded, quarantined, or retained as historical evidence and cannot close the new generation
