## ADDED Requirements

### Requirement: Prompt Assets Are Model-Visible Contract Inputs
FlowPilot SHALL treat prompt cards, shared prompt assets, manifests, and prompt hashes as executable contract inputs for model-test-code diagnostics.

#### Scenario: Prompt asset drift is observed
- **WHEN** a prompt/card asset changes after the last prompt-boundary evidence
- **THEN** FlowPilot marks the related code-boundary or model-test evidence stale until the prompt asset is revalidated

#### Scenario: Prompt manifest participates in contract check
- **WHEN** install readiness validates prompt boundary policy
- **THEN** the check consumes the runtime card manifest or prompt manifest rather than scanning only Python source text

### Requirement: Prompt Boundary Gaps Feed Maturation
Prompt boundary validation SHALL feed missing or stale prompt-contract evidence into the model maturation gate.

#### Scenario: Missing prompt observation becomes maturation signal
- **WHEN** a model-owned behavior depends on a prompt asset but no current code-boundary observation names that asset
- **THEN** FlowPilot emits an `add_code_boundary_observation` or `add_model_obligation` maturation action
