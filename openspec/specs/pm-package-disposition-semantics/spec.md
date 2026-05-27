# pm-package-disposition-semantics Specification

## Purpose
TBD - created by archiving change harden-package-disposition-semantics. Update Purpose after archive.
## Requirements
### Requirement: PM package disposition identity is semantic
The Router SHALL treat a PM package-result disposition as identified by router event, batch id, packet ids, and packet generation id. The role-output body hash SHALL be retained as audit and conflict evidence, but MUST NOT create a second ordinary disposition identity for the same package.

#### Scenario: Same package different body conflicts
- **WHEN** a PM package-result disposition has already been recorded for a batch/generation
- **AND** a later disposition for the same router event, batch id, packet ids, and packet generation id has a different body hash
- **THEN** the Router rejects the later event as a conflicting package disposition
- **AND** the Router does not write a second PM disposition or advance the batch

#### Scenario: Same package same body replays
- **WHEN** a PM package-result disposition is replayed with the same semantic identity and same body hash
- **THEN** the Router returns an idempotent already-recorded result
- **AND** any stale matching wait row may be closed without duplicate package side effects

### Requirement: PM package dispositions carry per-packet outcomes
The PM package-result disposition SHALL represent worker-specific acceptance, rework, block, cancellation, or route/node mutation decisions as per-packet outcomes inside the single authoritative package disposition.

#### Scenario: One worker accepted and one worker needs rework
- **WHEN** one member packet result is usable and another member packet requires rework
- **THEN** the PM records one package disposition with separate packet outcomes for both packet ids
- **AND** the aggregate disposition is not `absorbed`

#### Scenario: All packets accepted
- **WHEN** all member packet outcomes are accepted
- **THEN** the PM may record an `absorbed` aggregate disposition
- **AND** the Router may release the formal reviewer package only after the existing source-result self-check and reviewer-boundary requirements pass

### Requirement: PM package dispositions are shared across package kinds
The PM package-result disposition rules SHALL apply consistently to material-scan, research, and current-node result packages.

#### Scenario: Research package duplicate conflicts
- **WHEN** a research result package has one recorded PM disposition
- **AND** a different PM disposition body is submitted for the same research batch/generation
- **THEN** the Router rejects the later event under the same package conflict rule used for material-scan packages

#### Scenario: Current-node package duplicate conflicts
- **WHEN** a current-node result package has one recorded PM disposition
- **AND** a different PM disposition body is submitted for the same current-node batch/generation
- **THEN** the Router rejects the later event under the same package conflict rule used for material-scan packages

### Requirement: Repair creates a new package identity
Corrections to an already-dispositioned package SHALL use an authorized repair, cancellation, supersession, or reissue path that creates a new batch or packet generation rather than a second ordinary disposition for the old identity.

#### Scenario: New generation may receive a new disposition
- **WHEN** an authorized repair path supersedes an old package and creates a new batch/generation
- **THEN** the new package may receive its own PM package-result disposition
- **AND** stale progress flags or old dispositions do not cause the new package to be treated as already absorbed
