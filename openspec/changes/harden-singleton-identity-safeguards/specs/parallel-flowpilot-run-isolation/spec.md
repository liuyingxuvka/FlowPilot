## ADDED Requirements

### Requirement: Singleton Audit Respects Parallel Run Plurality
FlowPilot singleton audits SHALL distinguish intended parallel runs and Flow blocks from illegal duplicate authority inside one run or one targeted operation.

#### Scenario: Multiple background Flow blocks are legal
- **WHEN** the status projection contains more than one active or background Flow block
- **THEN** the singleton audit marks the plurality as legal only if operations still require an explicit target or all-target decision

#### Scenario: Untargeted operation is a conflict risk
- **WHEN** an operation would act on active run state without a run id, run root, or explicit all-runs scope
- **THEN** the singleton audit reports an authority risk rather than using the current pointer as global authority
