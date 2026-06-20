## MODIFIED Requirements

### Requirement: Unknown Binding Evidence Is A Liveness Hazard
The system SHALL reject role recovery readiness when the current role binding
cannot be proven addressable from current evidence.

#### Scenario: Unknown binding evidence is marked safe
- **WHEN** a role recovery state lacks current addressable role binding evidence
  but is incorrectly marked safe
- **THEN** the liveness hazard report MUST include
  `unknown_binding_evidence_marked_safe`
