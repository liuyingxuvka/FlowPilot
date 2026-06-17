## ADDED Requirements

### Requirement: Route-authority model-test binding
FlowGuard model-test alignment SHALL bind route-authority singularity obligations to owner code contracts and current passing test evidence before broad FlowPilot confidence can claim that wrong-path route actions cannot advance.

#### Scenario: New model obligations have test evidence
- **WHEN** the route-authority singularity model adds obligations for single owner, legal action set, wrong-path rejection feedback, no fallback acceptance, and corrected retry return
- **THEN** model-test alignment includes evidence rows that bind each obligation to router/runtime or synthetic replay tests

#### Scenario: Missing route-authority evidence blocks alignment
- **WHEN** a route-authority obligation lacks current passing test evidence or a code contract owner
- **THEN** model-test alignment reports a gap instead of marking the family green

### Requirement: Route-authority field lifecycle projection
Behavior-bearing route-authority fields SHALL be projected into FieldLifecycleMesh and model-test alignment when they are added to registries, prompt/card payloads, blockers, or runtime snapshots.

#### Scenario: Authority fields are accounted
- **WHEN** fields such as `current_owner`, `current_state_family`, `legal_next_actions`, `forbidden_actions`, and `required_repair_command` are introduced or expanded
- **THEN** the field lifecycle review records their owner, readers, writers, behavior impact, and old-field/no-fallback disposition
