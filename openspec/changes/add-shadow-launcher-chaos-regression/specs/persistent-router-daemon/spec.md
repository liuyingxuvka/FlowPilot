## ADDED Requirements

### Requirement: Shadow crash tests cover daemon and launcher recovery
The system SHALL test daemon shutdown, stale owner locks, interrupted launcher
startup, and resume rehydration through deterministic shadow packages.

#### Scenario: Daemon crash returns to resumable state
- **WHEN** a shadow run simulates daemon death or stale lock during fake AI
  package processing
- **THEN** the Router reports a resumable or blocked standard state and does
  not silently advance work from stale liveness evidence
