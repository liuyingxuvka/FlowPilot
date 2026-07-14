## ADDED Requirements

### Requirement: Workstream and resource-discovery tests participate in parent tiers
Focused tests for complete-workstream prompts, discovery field lifecycle, material special-path removal, canonical fake profiles, and Reviewer/PM semantics SHALL be registered under the smallest owning tier and its required release parents.

#### Scenario: Focused test passes but parent is stale
- **WHEN** a focused workstream test passes after source changes but the owning parent evidence predates those changes
- **THEN** parent confidence SHALL remain stale until rerun or valid proof reuse is established.

### Requirement: Background parents bind a frozen covered-source fingerprint
All, formal-submit-adversarial, release, repository final-confidence, Meta, and Capability background regressions SHALL record the covered-source fingerprint and final out/err/combined/exit/meta artifacts; a source change SHALL invalidate affected proof rather than silently preserving pass status.

#### Scenario: Source changes during background run
- **WHEN** a covered prompt, model, runtime, test, or tier file changes after the background run freezes its fingerprint
- **THEN** the run SHALL finish as stale/non-passing for final evidence
- **AND** the affected parent SHALL be rerun from the new freeze point.

### Requirement: Final confidence is an acyclic terminal consumer
Current all, formal-submit-adversarial, and release artifacts SHALL compile into the Acceptance TestMesh manifest before strict ContractExhaustion, Cartesian, Model-Test Alignment, Acceptance TestMesh, and ModelMesh consumers run. Repository final-confidence SHALL run only after those strict parents and SHALL NOT be embedded in release evidence or used to prove its own MTA input.

#### Scenario: Final confidence is placed inside release evidence
- **WHEN** release includes the final-confidence command, or TestMesh/MTA consumes a final-confidence result that itself invokes MTA
- **THEN** TestTiering SHALL reject the dependency graph as cyclic
- **AND** repository final-confidence SHALL remain a downstream terminal consumer
- **AND** formal terminal-return authority SHALL remain scoped to the active FlowPilot run's own final-preflight.
