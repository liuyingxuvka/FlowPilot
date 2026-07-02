## MODIFIED Requirements

### Requirement: Reviewer repair checks bind to current subject and dossier
FlowPilot reviewer packets for repair subjects SHALL include the active repair
dossier context and SHALL evaluate the current subject, not only the latest PM
plan text.

#### Scenario: Reviewer sees prior blocker chain
- **WHEN** Runtime issues a reviewer packet for a repair subject inside a
  repair dossier
- **THEN** the reviewer packet MUST authorize the prior blocker reports and
  reviewer reports needed to check whether the same issue was repaired.

#### Scenario: Reviewer keeps PM plan-stage review separate from worker evidence
- **WHEN** the reviewer packet subject is a PM node-context plan
- **AND** the `review_window` subject lifecycle stage is `node_plan_definition`
- **AND** the PM result does not claim already-produced worker evidence or
  repair closure evidence
- **THEN** Reviewer MUST judge the PM plan as a plan-stage subject
- **AND** Reviewer MUST NOT block solely because worker result artifacts,
  repaired worker evidence, or post-result FlowGuard evidence do not exist yet.

#### Scenario: Reviewer rejects plan-as-worker-evidence
- **WHEN** the reviewer packet subject is a worker/result-stage repair subject,
  or a PM plan that claims already-produced worker evidence or repair closure
  evidence
- **AND** the only available body is a PM node-context plan
- **THEN** Reviewer MUST block the subject as missing current evidence.

#### Scenario: Reviewer uses matching FlowGuard when required
- **WHEN** a repair subject requires FlowGuard evidence
- **THEN** the reviewer packet MUST authorize the matching current FlowGuard
  result for that subject
- **AND** a FlowGuard result for a different PM plan or old subject MUST NOT
  satisfy the review.
