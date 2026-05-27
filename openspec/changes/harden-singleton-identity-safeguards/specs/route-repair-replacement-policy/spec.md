## ADDED Requirements

### Requirement: Route Replacement Singleton Evidence
FlowPilot SHALL include route replacement and old active packet disposition in singleton evidence before a replacement branch can support route confidence.

#### Scenario: Replacement disposes old current work
- **WHEN** a replacement route branch becomes eligible for activation
- **THEN** singleton evidence records each old current packet, sibling evidence row, and affected route node as superseded, stale, quarantined, migrated, or blocking

#### Scenario: Undisposed old route authority blocks confidence
- **WHEN** old current route work remains active after replacement without a disposition
- **THEN** the singleton checker reports a duplicate current-route authority hazard
