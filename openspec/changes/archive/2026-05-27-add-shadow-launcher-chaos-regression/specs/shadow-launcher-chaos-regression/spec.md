## ADDED Requirements

### Requirement: Shadow launcher regressions cover installed startup to standard state
The system SHALL provide deterministic shadow-launcher regression evidence that
uses the installed FlowPilot skill and real Router/CLI control surfaces with
prepared fake AI artifacts.

#### Scenario: Installed launcher shadow flow reaches a standard state
- **WHEN** a prepared fake AI work package is run through the installed skill
  boundary and real Router/CLI startup path
- **THEN** the run records launcher/import evidence, Router actions, ACK or
  receipt gates, and a recognized standard state without direct state mutation

### Requirement: Crash recovery packages return to recognized recovery states
The system SHALL test stale locks, daemon/process shutdown, resume, and
progress-only proof failures as explicit recovery packages.

#### Scenario: Crash package is recoverable
- **WHEN** a fake AI package run is interrupted by stale lock, daemon death,
  duplicate resume, or progress-only background proof
- **THEN** the control plane returns to a blocked, recoverable, quarantined, or
  clean terminal state and does not count progress-only evidence as completion

### Requirement: Peer-agent conflict packages preserve run ownership
The system SHALL test peer-agent conflict packages that attempt to overwrite
  shared artifacts, reuse another run's proof, stop a peer run, or claim the
  same model-test evidence owner.

#### Scenario: Peer conflict cannot cross-contaminate runs
- **WHEN** two fake AI package flows write or validate against shared
  background, model-test, or run-state surfaces
- **THEN** each run's ownership, evidence freshness, and protected state remain
  isolated or the conflict is reported as a blocker

### Requirement: Malformed fake packages are rejected without protected mutation
The system SHALL provide a bounded malformed-package generator for finite bad
package classes.

#### Scenario: Generated bad package is rejected
- **WHEN** a generated bad package has missing fields, wrong role, wrong event,
  stale hash, stale proof, path mismatch, duplicate submit, or semantic overclaim
- **THEN** the package is rejected before protected state advances

### Requirement: Bounded soak loops detect residue and repeatability failures
The system SHALL provide a bounded soak regression that repeats startup,
recovery, package rejection, and terminal cleanup loops.

#### Scenario: Soak loop leaves no active residue
- **WHEN** the bounded soak loop completes multiple fake AI package cycles
- **THEN** every cycle has final evidence, no active stale lock, no active
  blocker unless intentionally expected, no reused proof overclaim, and no dirty
  terminal ledger
