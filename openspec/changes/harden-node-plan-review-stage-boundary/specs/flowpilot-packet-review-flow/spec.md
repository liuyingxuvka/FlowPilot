# flowpilot-packet-review-flow Delta

## ADDED Requirements

### Requirement: Node plan review uses plan-stage evidence
FlowPilot SHALL make ordinary `task.node_acceptance_plan` review use a
plan-stage evidence standard.

#### Scenario: PM node plan review does not require Worker artifacts
- **WHEN** PM submits `decision=pass` with a current top-level
  `node_context_package`
- **AND** Runtime issues a Reviewer packet for the staged
  `commit_node_acceptance_plan` effect
- **THEN** the Reviewer packet SHALL tell Reviewer to review PM plan quality,
  decomposition depth, evidence projection, risk coverage, and Worker
  dispatch readiness
- **AND** the Reviewer packet SHALL NOT require current Worker artifacts,
  per-output artifact payloads, post-result FlowGuard evidence, or fresh
  Worker-result checker output at this stage.

#### Scenario: Node plan review may still block shallow plans
- **WHEN** the PM node plan is too broad, too fine, wrongly ordered, missing
  proof obligations, missing test obligations, or unsafe to hand to Worker
- **THEN** Reviewer SHALL block the PM node plan through the existing review
  blocker and PM repair flow.

### Requirement: Worker result review uses result-stage evidence
FlowPilot SHALL make Worker-result review use a result-stage evidence
standard.

#### Scenario: Worker result review requires current artifacts and FlowGuard
- **WHEN** Worker submits a node result after an accepted node plan
- **THEN** Runtime SHALL issue post-result FlowGuard before independent
  Reviewer result review
- **AND** Reviewer result review SHALL require current artifacts, direct
  evidence, applicable checker output, and matching post-result FlowGuard
  evidence before pass.

#### Scenario: Worker result prose cannot substitute for artifacts
- **WHEN** a Worker result only claims success in prose and lacks required
  current artifacts, direct evidence, or checker output
- **THEN** FlowGuard or Reviewer SHALL block the Worker result using the
  existing blocker and PM repair flow.

### Requirement: Old node prework FlowGuard remains unsupported
FlowPilot SHALL keep `node_prework_flowguard` unsupported for current ordinary
node execution.

#### Scenario: Old prework packet is not accepted as current evidence
- **WHEN** an old or stale `node_prework_flowguard` packet or result appears in
  a current run
- **THEN** Runtime SHALL reject or quarantine it through current blocker/repair
  handling
- **AND** Runtime SHALL NOT translate it into a valid current
  `node_acceptance_plan`, Worker result, post-result FlowGuard report, or
  Reviewer pass.
