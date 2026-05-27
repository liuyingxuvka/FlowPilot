## ADDED Requirements

### Requirement: Remaining heavy owners are split by behavior family
FlowPilot SHALL split the remaining heavy runtime/model owner modules by
cohesive behavior family while preserving existing facade entrypoints.

#### Scenario: Packet control-plane transition facade remains compatible
- **WHEN** model code imports transitions from `packet_control_plane_model_transitions.py`
- **THEN** all existing transition classes remain available
- **AND** phase-specific transition bodies are owned by focused child modules.

#### Scenario: Router export manifest remains compatible
- **WHEN** the router facade export installer reads `OWNER_EXPORTS`
- **THEN** the existing registry contract remains available
- **AND** domain manifest shards provide the underlying export rows.

#### Scenario: Runtime owner facades remain compatible
- **WHEN** existing router code calls action-factory, PM role-work, terminal, or
  Controller scheduler/receipt helper names
- **THEN** the names remain import-compatible through their existing owner files
- **AND** large behavior families are moved into focused child owners.

### Requirement: Splits are not micro-module explosions
FlowPilot SHALL avoid one-function-per-file splits and SHALL group helpers by
behavior family, state ownership, and validation boundary.

#### Scenario: StructureMesh reviews owner shape
- **WHEN** StructureMesh checks inspect this polish pass
- **THEN** missing owner, duplicate owner, removed facade, stale parity,
  insufficient evidence, and micro-module hazards are represented
- **AND** the accepted target structure shows coarse owner families.

### Requirement: Prompt text movement remains manifest-protected
FlowPilot SHALL only externalize prompt-like text when missing/stale assets can
be detected by executable validation.

#### Scenario: Prompt asset moved from Python
- **WHEN** a prompt-like instruction block is moved to `runtime_kit/prompts/`
- **THEN** the prompt manifest records its path/hash/template variables
- **AND** tests or FlowGuard evidence fail on missing, stale, or undeclared
  prompt assets.

### Requirement: Local completion gates are release-grade but local-only
FlowPilot SHALL complete this maintenance pass with local install freshness,
hidden regression evidence, and a local git commit without remote publication.

#### Scenario: Hidden background regressions are claimed complete
- **WHEN** router, Meta, or Capability regressions are reported complete
- **THEN** their stdout, stderr, combined, exit, and meta artifacts exist
- **AND** final exit/meta evidence, not progress output alone, supports the
  pass claim.

#### Scenario: Local install and git are synchronized
- **WHEN** the pass is complete
- **THEN** the installed local FlowPilot skill matches the repository source
- **AND** the work is committed locally on `main`
- **AND** no GitHub push, tag, or release publication occurs.
