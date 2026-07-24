## ADDED Requirements

### Requirement: Retention planning proves eligibility before ranking
The existing retention entry SHALL default to read-only planning and SHALL
classify current/index identity, terminal proof, live daemon/process/lease,
open packet/action, write lock, external reference, pin, bytes, and protected
reasons for each run or validation directory.  Count or age limits SHALL rank
only entries already proven eligible.

#### Scenario: Current or live run is inspected
- **WHEN** retention planning inspects the current run or a run with any live owner evidence
- **THEN** the entry is protected and ineligible for archive/apply
- **AND** `max_runs`, age, or disk pressure cannot override the protection

#### Scenario: Terminal unreferenced run is inspected
- **WHEN** a non-current run has valid terminal proof, zero live owners, zero open work, zero locks, and zero external references or pins
- **THEN** the read-only plan may mark it eligible and record a proposed archive action

### Requirement: Archive apply is an explicit frozen transaction
Archive/apply SHALL require an explicitly supplied current plan path and
SHA-256.  It SHALL revalidate all protections, create and read back a ZIP,
record the archive path/hash/time in the existing run index, and only then
remove archived heavy subdirectories.  Any changed or ambiguous protection
SHALL stop before destructive action.

#### Scenario: Plan remains current
- **WHEN** explicit apply receives the exact frozen plan and every candidate remains eligible
- **THEN** each archive is verified before the index records its archive identity
- **AND** heavy source subdirectories are removed only after the durable archive and index commit

#### Scenario: Candidate becomes referenced after planning
- **WHEN** a candidate acquires a checkpoint, proof, release, pin, lease, lock, open work item, or live owner after the plan was frozen
- **THEN** apply blocks that candidate without deleting or archiving its heavy material

### Requirement: Installation and validation never auto-clean real history
FlowPilot install, normal validation, SkillGuard maintenance, and release
workflows SHALL NOT automatically apply retention to real historical runs or
validation directories.

#### Scenario: Release validation completes
- **WHEN** release validation and installation succeed
- **THEN** retention plan/apply capability is available and tested
- **AND** no historical run or validation directory is archived or deleted unless apply was separately invoked with its exact plan
