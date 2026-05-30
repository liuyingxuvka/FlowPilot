## ADDED Requirements

### Requirement: Mature FlowGuard projects read topology before non-trivial work
FlowPilot and FlowGuard-facing prompt surfaces SHALL instruct agents to read a
current FlowGuard project topology artifact before non-trivial planning,
implementation, review, repair, validation, or completion decisions in a
mature FlowGuard project.

#### Scenario: Agent enters mature FlowGuard project
- **WHEN** repository instructions or runtime cards identify a mature FlowGuard
  project with `docs/flowguard_project_topology.md`
- **THEN** the agent MUST read the topology before non-trivial work
- **AND** the agent MUST use it as background architecture rather than
  validation evidence.

#### Scenario: FlowPilot PM plans a route
- **WHEN** PM prepares product architecture, route skeleton, node acceptance,
  repair, or closure decisions in a FlowGuard-heavy run
- **THEN** the prompt MUST require PM to consider the topology's relevant model,
  test, code, evidence, and known-bad areas before selecting downstream work.

#### Scenario: Officer or Reviewer consumes topology
- **WHEN** a FlowGuard Officer or Reviewer card references topology
- **THEN** it MUST preserve existing role authority
- **AND** it MUST forbid using topology to approve gates, mutate routes, or
  replace file-backed FlowGuard reports.

### Requirement: Prompt surfaces maintain topology after topology-affecting changes
FlowPilot and repository instructions SHALL require topology rebuild/check when
an agent changes FlowGuard models, runners, test registries, code ownership
surfaces, result artifact paths, prompt/card boundaries, or validation
readiness surfaces.

#### Scenario: Model or test surface changes
- **WHEN** a task modifies a FlowGuard model, check runner, model-test
  alignment family, test-tier registry, or ordinary test evidence mapping
- **THEN** the agent MUST rebuild and check the topology before claiming done
  or explicitly report why the topology is intentionally stale.

#### Scenario: Code ownership surface changes
- **WHEN** a task splits, moves, adds, or removes a code owner surface that is
  represented by FlowGuard topology
- **THEN** the agent MUST refresh the topology and run the relevant readiness
  checks before install synchronization.
