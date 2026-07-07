## ADDED Requirements

### Requirement: Reviewer challenge chain has focused validation
FlowPilot SHALL validate Reviewer/PM challenge-chain changes through focused
tests before broad confidence is claimed.

#### Scenario: Prompt and card coverage is checked
- **WHEN** Reviewer or PM prompt/card text changes for this chain
- **THEN** focused card-instruction coverage tests SHALL prove fixed stage
  mappings, concrete Reviewer challenge guidance, concrete PM suggestion
  disposition guidance, and absence of weak mechanical pass examples.

#### Scenario: Runtime and fake-AI coverage is checked
- **WHEN** review-window projection or fake-AI behavior changes
- **THEN** focused runtime and AI contract projection tests SHALL prove
  complete review-window projection, fake-AI Cartesian coverage, specific
  challenge profiles, and generic low-quality profiles.

### Requirement: Install and model evidence are refreshed after prompt/runtime changes
FlowPilot SHALL refresh install sync, topology, and affected FlowGuard model
evidence after review-window, prompt/card, fake-AI, or test surfaces change.

#### Scenario: Local install sync is checked
- **WHEN** implementation changes FlowPilot skill assets, runtime assets, or
  templates
- **THEN** local install sync and install self-check commands SHALL be run
  before claiming the installed version is current.

#### Scenario: Topology and models are refreshed
- **WHEN** runtime, prompt/card boundaries, model runners, tests, or validation
  readiness surfaces change
- **THEN** topology build/check and the affected FlowGuard model regressions
  SHALL be refreshed or explicitly reported as skipped with impact.
