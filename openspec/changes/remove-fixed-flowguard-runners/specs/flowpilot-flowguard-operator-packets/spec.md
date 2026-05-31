## MODIFIED Requirements

### Requirement: FlowPilot dispatches FlowGuard operator packets without repository-specific runner assumptions
FlowPilot SHALL issue FlowGuard operator packets with the modeled target,
subject result, node context when available, and a run-local evidence policy,
but it SHALL NOT include fixed runner recommendations for repository-specific
Meta or Capability scripts.

#### Scenario: Runtime issues a FlowGuard check packet
- **WHEN** a PM, worker, or node result requires FlowGuard operator evidence
- **THEN** the packet body SHALL include `evidence_output_policy.run_local_evidence_root`
- **AND** the packet body SHALL include the modeled target and target result id
- **AND** the packet body SHALL NOT include `recommended_runner_commands`
- **AND** the packet instruction SHALL leave model/check selection to the FlowGuard operator.

#### Scenario: Target repository lacks FlowPilot source runners
- **WHEN** a target repository does not contain `simulations/run_meta_checks.py`
  or `simulations/run_capability_checks.py`
- **THEN** FlowPilot SHALL NOT have instructed FlowGuard operator to run those
  missing scripts by default
- **AND** FlowGuard operator SHALL be able to record selected existing evidence,
  newly created run-local evidence, skipped checks, residual risks, or a real
  evidence blocker based on the target project context.

### Requirement: FlowPilot preserves run-local evidence and baseline boundaries
FlowPilot SHALL keep formal-run FlowGuard evidence under the packet's run-local
evidence root unless a packet explicitly requests a source-controlled baseline
refresh.

#### Scenario: FlowGuard packet includes evidence output policy
- **WHEN** the runtime issues a FlowGuard operator packet
- **THEN** the packet SHALL include the run-local evidence root
- **AND** it SHALL warn that tracked `simulations/*_results.json` baselines are
  forbidden unless an explicit baseline update is requested.

### Requirement: FlowPilot blocks structured failing FlowGuard outcomes
FlowPilot SHALL classify structured FlowGuard outputs that declare blocked
verdicts or failing nested FlowGuard reports as blocking outcomes.

#### Scenario: FlowGuard result uses verdict
- **WHEN** a result body contains structured JSON with `"verdict": "blocked"`
- **THEN** the runtime SHALL record the packet result as blocked
- **AND** it SHALL create the normal active blocker path.

#### Scenario: FlowGuard result nests a failing report
- **WHEN** a result body contains structured JSON with
  `"flowguard_report": {"ok": false}`
- **THEN** the runtime SHALL record the packet result as blocked
- **AND** it SHALL not default that result to pass because no top-level
  `decision` or `status` field was present.
