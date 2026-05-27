## ADDED Requirements

### Requirement: Singleton Gaps Are Model Maturation Signals
FlowPilot model maturation SHALL consume singleton authority gaps, duplicate singleton hazards, stale singleton proof, and progress-only singleton evidence as required maturation signals.

#### Scenario: Missing singleton ownership becomes a model action
- **WHEN** singleton evidence lacks a scope, owner, identity key, generation key, or old-object disposition
- **THEN** model maturation emits a concrete action such as `add_model_obligation`, `add_code_boundary_observation`, `refresh_evidence`, `split_child_model`, or `downgrade_claim`

#### Scenario: Duplicate hazard prevents full maturation closure
- **WHEN** a singleton duplicate hazard is unresolved
- **THEN** model maturation reports scoped confidence or blocked confidence rather than full closure
