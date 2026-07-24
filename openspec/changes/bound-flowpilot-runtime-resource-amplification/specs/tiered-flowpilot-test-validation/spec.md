## ADDED Requirements

### Requirement: Raw background streams are stored once
Each background child SHALL retain stdout and stderr as the sole raw stream
bodies.  The stable `combined.txt` artifact SHALL be a bounded terminal index
of stream paths, hashes, byte/line counts, status, exit, timing, and cleanup
state and SHALL NOT contain copied raw stdout or stderr.

#### Scenario: Child emits large stdout and stderr
- **WHEN** a background child emits large content on both streams
- **THEN** the raw bytes appear only in the respective out and err artifacts
- **AND** combined output is at most 32 KiB and contains references rather than the stream bodies

#### Scenario: A raw stream changes
- **WHEN** stdout or stderr content changes after proof creation
- **THEN** the owner result fingerprint no longer matches
- **AND** the altered proof cannot be reused

### Requirement: V5 owner-reference evidence is the sole normal authority
Normal background impact planning and proof reuse SHALL accept only the direct
current `acceptance_testmesh_evidence_manifest.v5` contract.  It SHALL store one
immutable impact plan, bounded progress, a terminal owner index, and immutable
proof references.  V4 files SHALL be historical audit material only and SHALL
be rejected by normal runtime without conversion, newest-manifest discovery,
fallback, dual read, or dual emission.

#### Scenario: Explicit V5 seed baseline
- **WHEN** no current V5 authority exists and the source/toolchain/owner inventory is frozen
- **THEN** one explicit seed-baseline execution runs every required owner and produces the first complete V5 manifest

#### Scenario: V4 is supplied to normal runtime
- **WHEN** a caller supplies a V4 manifest or its SHA-256 as current proof input
- **THEN** normal runtime rejects the input with a current-contract error
- **AND** it does not search for another manifest or convert V4

#### Scenario: Reused owner is projected into V5
- **WHEN** an unchanged owner has an exact current terminal proof and `TestResultReuseTicket`
- **THEN** V5 records the prior proof reference, ticket identity, and covered obligations
- **AND** it does not copy the prior raw logs, owner row, input snapshot, or complete ticket body

### Requirement: Supervisor progress is size-bounded
The background supervisor SHALL keep its immutable impact plan and terminal
owner proof index separate from a small mutable progress artifact.  Rewriting
progress SHALL NOT copy complete plans, snapshots, owner rows, or prior proof
bodies.

#### Scenario: Large owner inventory runs
- **WHEN** a background parent supervises a large mix of execute and reuse owners
- **THEN** progress updates contain only owner ids, states, counts, and recent timing
- **AND** reused proof bodies remain only at their immutable referenced paths

### Requirement: Background process ownership preserves edge lineage
Every process admitted to a background owner's descendant set SHALL preserve
orderable start-token lineage across every parent-child edge. A stale or reused
Windows parent PID SHALL stop traversal at that edge and SHALL NOT bridge the
owner into a pre-existing process or a younger sibling execution owner.

#### Scenario: Reused parent PID appears between parallel owners
- **WHEN** a Windows process snapshot links a current child to an older reused PID and then links that PID to a younger sibling owner
- **THEN** descendant traversal stops before the older PID
- **AND** the younger sibling is not terminated, settled, or recorded as the current owner's descendant
- **AND** cleanup evidence remains scoped to the exact execution owner
