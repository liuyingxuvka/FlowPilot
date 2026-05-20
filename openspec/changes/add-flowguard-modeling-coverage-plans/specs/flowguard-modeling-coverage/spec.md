## ADDED Requirements

### Requirement: FlowPilot generates a startup FlowGuard capability snapshot
FlowPilot Router SHALL generate one run-scoped FlowGuard capability snapshot before PM product modeling starts.

#### Scenario: Startup snapshot records current FlowGuard menu
- **WHEN** a formal FlowPilot run reaches the PM product modeling stage
- **THEN** the run SHALL contain `.flowpilot/runs/<run-id>/flowguard/capability_snapshot.json`
- **AND** the snapshot SHALL record FlowGuard importability, schema/version evidence, relevant FlowGuard skill routes, source paths, content hashes, and generation time.
- **AND** the snapshot SHALL record portable resolution roots and SHALL NOT require a user-specific hardcoded filesystem path.

#### Scenario: PM does not use stale fixed FlowGuard menu
- **WHEN** PM writes product or process modeling plans
- **THEN** those plans SHALL reference the current run's `flowguard_capability_snapshot_id`
- **AND** PM SHALL NOT rely on an unversioned prompt-only FlowGuard capability list.

### Requirement: PM writes a product modeling plan before Product Officer modeling
FlowPilot SHALL require PM to write a Product Modeling Plan before Product FlowGuard Officer produces the product model family.

#### Scenario: Product model families are declared before modeling
- **WHEN** Product FlowGuard Officer is asked to model product behavior
- **THEN** PM SHALL have written `flowguard/product_modeling_plan.json`
- **AND** the plan SHALL list product model families to build, families merged into another model, families intentionally skipped, merge/skip reasons, and Product Officer role-skill bindings from the startup snapshot.

#### Scenario: Single product model overcollapse is rejected
- **WHEN** a task has UI, user-visible state, failure/recovery, validation, data, or other distinct product risk families
- **THEN** PM SHALL either assign separate model families or record an explicit merge reason
- **AND** Reviewer or PM model acceptance SHALL reject an unreasoned single-model report.

### Requirement: Product Officer reports a product model family
FlowPilot SHALL require Product FlowGuard Officer output to satisfy the accepted Product Modeling Plan instead of assuming one product model is sufficient.

#### Scenario: Product Officer covers planned families
- **WHEN** Product Officer submits a product behavior model report
- **THEN** the report SHALL reference the startup snapshot and Product Modeling Plan
- **AND** it SHALL list each planned product model family as covered, merged with reason, blocked, or split-requested.

#### Scenario: Missing planned family blocks PM acceptance
- **WHEN** Product Officer omits a planned product family without a merge, blocker, or split request
- **THEN** PM SHALL request product model rebuild before product architecture challenge, root contract freeze, or route drafting.

### Requirement: PM selects ordinary child skills after product model acceptance
FlowPilot SHALL use the accepted product model family as the basis for ordinary child-skill selection and child-skill manifest projection.

#### Scenario: Child-skill selection consumes product model family
- **WHEN** PM writes child-skill selection and child-skill gate manifest
- **THEN** PM SHALL reference the accepted product model family report and Product Modeling Plan
- **AND** selected child skills SHALL map standards to product capabilities, route nodes, worker packets, reviewer gates, and officer gates where relevant.

#### Scenario: Manifest-only evidence cannot close model-family coverage
- **WHEN** child-skill manifest review passes
- **THEN** FlowPilot SHALL NOT treat the manifest alone as Product Officer or Process Officer model-family coverage
- **AND** unclosed model families SHALL remain unresolved until accepted through the relevant modeling plan and officer report.

### Requirement: PM writes a process modeling plan before Process Officer modeling
FlowPilot SHALL require PM to write a Process Modeling Plan before Process FlowGuard Officer produces the process model family.

#### Scenario: Process model families are declared before modeling
- **WHEN** Process FlowGuard Officer is asked to model route viability
- **THEN** PM SHALL have written `flowguard/process_modeling_plan.json`
- **AND** the plan SHALL list process model families for route hierarchy, leaf readiness, child-skill conformance, validation/replay flow, repair-return paths, and any other task-specific process risk.

#### Scenario: Process plan consumes product and child-skill sources
- **WHEN** PM writes the Process Modeling Plan
- **THEN** the plan SHALL reference the accepted product model family, child-skill manifest, and startup FlowGuard capability snapshot
- **AND** it SHALL state how process models must cover the product model family.

### Requirement: Process Officer reports a process model family
FlowPilot SHALL require Process FlowGuard Officer output to satisfy the accepted Process Modeling Plan and prove process coverage of the product model family.

#### Scenario: Process Officer covers planned families
- **WHEN** Process Officer submits a route process model report
- **THEN** the report SHALL reference the startup snapshot, Product Modeling Plan, Product Officer report, child-skill manifest, and Process Modeling Plan
- **AND** it SHALL list each planned process model family as covered, merged with reason, blocked, or split-requested.

#### Scenario: Route activation waits for model-family acceptance
- **WHEN** PM attempts to activate a reviewed route
- **THEN** FlowPilot SHALL require accepted product and process model-family decisions
- **AND** route activation SHALL remain blocked if planned families are missing, unresolved, or covered only by manifest/reviewer prose.

### Requirement: Final closure verifies modeling coverage
FlowPilot SHALL verify the startup snapshot, PM modeling plans, officer model-family reports, child-skill projection, and validation evidence before terminal completion.

#### Scenario: Final ledger closes all model families
- **WHEN** PM builds the final route-wide gate ledger
- **THEN** the ledger SHALL reference the startup FlowGuard capability snapshot, Product Modeling Plan, accepted product model-family report, Process Modeling Plan, accepted process model-family report, child-skill manifest, and validation evidence.

#### Scenario: Final ledger blocks unresolved model coverage
- **WHEN** a planned model family is missing, stale, manifest-only, or skipped without reason
- **THEN** terminal completion SHALL remain blocked until PM repairs the model plan, accepts a justified merge/skip, or reruns the relevant officer model.
