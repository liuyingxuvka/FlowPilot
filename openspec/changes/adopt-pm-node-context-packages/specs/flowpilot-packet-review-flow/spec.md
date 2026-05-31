## MODIFIED Requirements

### Requirement: Reviewer reviews formal packages, not dispatch requests

FlowPilot SHALL keep Reviewer review on PM-built formal gate packages, current
node context packages, and independent quality/source/fact checks, not
pre-dispatch approval of PM-authored worker packets.

#### Scenario: Reviewer quality gate starts from node context

- **WHEN** runtime issues a Reviewer packet for a node worker result
- **THEN** the packet MUST include the current PM node context package for that
  node as starting evidence
- **AND** Reviewer SHALL inspect the formal package, subject result, FlowGuard
  report, and required direct evidence before pass or block.

#### Scenario: Node context package is not a scope limit

- **WHEN** a PM node context package lists starting references or inspection
  targets
- **THEN** Reviewer SHALL treat those entries as a required minimum checklist
- **AND** Reviewer MAY inspect additional files, screenshots, UI surfaces, logs,
  commands, model artifacts, and evidence paths inside the authorized scope.
