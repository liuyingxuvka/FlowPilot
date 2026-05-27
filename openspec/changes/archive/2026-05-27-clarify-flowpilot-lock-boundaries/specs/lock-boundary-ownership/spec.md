# lock-boundary-ownership Specification

## Purpose

Define the ownership boundary between FlowPilot runtime JSON write locks, Router
daemon single-writer locks, and packet active-holder leases.

## ADDED Requirements

### Requirement: Lock concepts remain separate

FlowPilot SHALL keep runtime JSON write locks, Router daemon locks, and packet
active-holder leases as distinct ownership domains with separate meaning,
persisted artifacts, and validation responsibilities.

#### Scenario: Runtime JSON write lock is encountered

- **WHEN** a daemon-critical JSON file has a `.write.lock` file
- **THEN** the runtime JSON write-lock owner decides whether to wait, take over
  a dead owner, or surface runtime write-in-progress metadata
- **AND** the packet active-holder lease path is not used to resolve the file
  write lock.

#### Scenario: Router daemon lock is checked

- **WHEN** a run-scoped `runtime/router_daemon.lock` file is checked
- **THEN** the Router daemon owner decides whether to attach, restart, replace
  explicitly, release, or report terminal/error status
- **AND** the runtime JSON write-lock owner does not decide daemon lifecycle.

#### Scenario: Packet active-holder lease is issued

- **WHEN** Router issues an active-holder lease for a packet
- **THEN** packet runtime records the lease as packet protocol authority for the
  current holder role and agent
- **AND** the lease is not treated as a filesystem lock or daemon single-writer
  lock.

### Requirement: Process liveness has one helper owner

FlowPilot SHALL use one shared process-liveness helper for platform-specific pid
checks while leaving lock-domain decisions in their existing owner modules.

#### Scenario: Runtime writer liveness is classified

- **WHEN** runtime JSON write-lock liveness needs to know whether a pid is live
- **THEN** it calls the shared process-liveness helper
- **AND** it still classifies active writer, dead-owner takeover, or stale
  takeover in the runtime JSON write-lock owner.

#### Scenario: Router daemon liveness is classified

- **WHEN** Router daemon lock liveness needs to know whether the owner pid is
  live
- **THEN** it calls the shared process-liveness helper
- **AND** it still classifies live daemon, stale daemon, released lock, or
  terminal/error state in the Router daemon owner.

### Requirement: Boundary evidence stays executable

FlowPilot SHALL back lock-boundary ownership changes with executable owner
boundary and StructureMesh evidence, not documentation alone.

#### Scenario: Boundary helper changes

- **WHEN** the shared process-liveness helper or one of its lock-domain callers
  changes
- **THEN** focused router boundary tests and StructureMesh checks must pass
  before the change is considered complete.
