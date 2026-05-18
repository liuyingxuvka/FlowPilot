## MODIFIED Requirements

### Requirement: FlowPilot maintenance passes keep executable evidence
FlowPilot repository maintenance SHALL use executable FlowGuard/OpenSpec
evidence for non-trivial structure changes and SHALL not treat prose-only
planning as completion evidence.

#### Scenario: Final owner polish completes locally
- **WHEN** the final owner polish pass is reported complete
- **THEN** OpenSpec validation passes
- **AND** StructureMesh/TestMesh/model-alignment checks pass
- **AND** focused tests for touched owners pass
- **AND** hidden background router/Meta/Capability artifacts show final success
- **AND** local install freshness and local git status are verified.
