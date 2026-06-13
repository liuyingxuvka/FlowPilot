## ADDED Requirements

### Requirement: Target-realization obligations bind to model and test evidence

FlowPilot FlowGuard alignment SHALL map target-realization obligations to prompt cards, templates, runtime gates, route/node artifacts, worker packet projections, final closure checks, and negative regression tests.

#### Scenario: Obligation has downstream coverage

- **WHEN** a target-realization obligation is accepted
- **THEN** model-test alignment names the downstream prompt/template/runtime/test surfaces that preserve or validate that obligation

#### Scenario: Obligation disappears downstream

- **WHEN** a target-realization obligation is accepted but missing from route, node, worker, or closure evidence
- **THEN** model-test alignment reports a gap before broad completion confidence
