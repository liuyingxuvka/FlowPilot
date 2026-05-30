## ADDED Requirements

### Requirement: System validation pass automatically closes the subject
The fresh FlowPilot runtime SHALL record a system-owned closure after passed
system validation and SHALL apply closure side effects without issuing an
ordinary Closure Officer packet.

#### Scenario: Reviewer pass auto-closes after system validation
- **WHEN** a subject packet has an accepted result, matching FlowGuard evidence,
  and a reviewer pass
- **THEN** the runtime MUST record passed validation evidence owned by the
  system
- **AND** the runtime MUST record a system closure for the subject packet
- **AND** the runtime MUST apply the subject's closure side effects
- **AND** the runtime MUST NOT issue a new Closure Officer packet for that
  ordinary success path.
- **AND** the runtime MUST NOT issue a validator packet for that ordinary
  success path.

#### Scenario: Closure remains a state transition
- **WHEN** system validation passes
- **THEN** the runtime MUST still record a closure/accounting artifact
- **AND** downstream route movement MUST happen through the closure side-effect
  logic, not directly from reviewer pass.

### Requirement: System validation failure routes to PM repair
The runtime SHALL convert failed system validation into a repairable blocker
owned by the PM repair process.

#### Scenario: Missing system-validation evidence blocks closure
- **WHEN** system validation records failed evidence for a subject packet
- **THEN** the runtime MUST NOT system-close the subject
- **AND** the runtime MUST record an active system-validation blocker
- **AND** the runtime MUST issue a PM repair decision packet
- **AND** the subject MUST remain blocked until the required recheck passes.

### Requirement: Validator and Closure Officer are not dispatchable roles
The clean new FlowPilot runtime SHALL NOT expose validator or Closure Officer
as leaseable responsibilities or packet kinds.

#### Scenario: Clean role set excludes old validation and closure workers
- **WHEN** a fresh runtime run dispatches work
- **THEN** the runtime MUST dispatch only PM, worker-class, FlowGuard, reviewer,
  research, or QA roles
- **AND** the runtime MUST reject `validation` and `closure` packet kinds
- **AND** the runtime MUST reject `validator` and `closure_officer`
  responsibilities.

### Requirement: Staged high-risk PM decisions apply after system closure
The runtime SHALL apply staged high-risk PM repair and PM disposition decisions
only after FlowGuard, reviewer, system validation, and system closure pass for
the PM decision subject.

#### Scenario: PM route mutation applies after system closure
- **WHEN** PM submits a staged route mutation decision
- **AND** the PM decision subject passes FlowGuard, review, and system
  validation
- **THEN** the runtime MUST system-close the PM decision subject
- **AND** the runtime MUST apply the staged route mutation
- **AND** the runtime MUST NOT require a Closure Officer packet.
