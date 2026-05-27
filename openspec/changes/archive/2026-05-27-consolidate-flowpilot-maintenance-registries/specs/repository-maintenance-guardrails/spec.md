# repository-maintenance-guardrails Delta

## ADDED Requirements

### Requirement: Registry consolidation preserves compatibility evidence

Repository maintenance SHALL prove that registry-derived compatibility views match the previously exported tables before switching behavior-sensitive callers to the registry.

#### Scenario: Generated table parity is checked before caller migration

- **GIVEN** a canonical registry replaces a hand-written protocol table
- **WHEN** maintenance migrates runtime callers to the derived view
- **THEN** a focused parity test proves the derived table matches the previous exported names and values
- **AND** the final maintenance report names that parity evidence.

### Requirement: Local git completion excludes unrelated worktree changes

Repository maintenance SHALL keep local git completion scoped to the current change and avoid staging unrelated pre-existing edits.

#### Scenario: Dirty worktree has unrelated files

- **GIVEN** the worktree contains modified files outside the maintenance registry consolidation scope
- **WHEN** the change is staged or committed
- **THEN** only files intentionally changed for this OpenSpec change are staged
- **AND** unrelated files remain untouched and are named as pre-existing if relevant.
