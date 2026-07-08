## ADDED Requirements

### Requirement: No-Fallback Claims Use Behavior Commitments
FlowPilot SHALL represent broad no-fallback maintenance claims as explicit
behavior commitments before assigning downstream model, field, test, or release
evidence.

#### Scenario: Broad no-fallback behavior is claimed
- **WHEN** maintenance claims that FlowPilot rejects old packets, duplicate packages, stale route evidence, fallback result paths, or unsupported field aliases
- **THEN** the claim SHALL identify the external behavior commitment, current owner, required evidence, downstream dependencies, and release scope.

### Requirement: Path-Sensitive Commitments Use One Primary Authority
FlowPilot SHALL route path-sensitive behavior commitments through one Primary
Path Authority that names the current primary runtime authority and rejects
automatic alternate success after primary failure.

#### Scenario: Primary path fails
- **WHEN** the primary current packet/result/gate/route path rejects or blocks an input
- **THEN** no helper, compatibility alias, fallback parser, historical artifact, old field, or alternate route path SHALL convert that same input into accepted success.

#### Scenario: Alternate path is intentionally removed
- **WHEN** a previous alternate path is no longer supported
- **THEN** FlowPilot SHALL keep the old name only in forbidden/deleted lists, negative tests, or historical labels
- **AND** runtime SHALL reject the path rather than translate it into the primary path.

### Requirement: PPA Evidence Projects To Tests And Risk Gates
Primary Path Authority evidence SHALL project canonical negative cases into
ContractExhaustionMesh, TestMesh, Model-Test Alignment, and final risk evidence
before supporting broad completion.

#### Scenario: PPA matrix is generated
- **WHEN** maintenance defines a PPA boundary for a path-sensitive FlowPilot behavior
- **THEN** each primary-failure and alternate-success case SHALL have a canonical case or shard id, an expected reject/block/repair oracle, and downstream test or alignment evidence.
