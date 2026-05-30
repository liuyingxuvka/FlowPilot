# runtime-structure-clarity Specification

## Purpose
TBD - created by archiving change final-runtime-clarity-pass. Update Purpose after archive.
## Requirements
### Requirement: Runtime modules have explicit owner boundaries
The FlowPilot runtime SHALL keep large behavior clusters behind unsupported historical facades while moving cohesive implementation bodies into explicit owner modules.

#### Scenario: Packet runtime facade remains compatible
- **WHEN** code imports or invokes the existing `packet_runtime.py` public functions or CLI
- **THEN** the same public entrypoints remain available
- **AND** packet creation, progress, result, handoff, audit, and CLI behavior are owned by focused child modules.

#### Scenario: Card runtime facade remains compatible
- **WHEN** code imports or invokes the existing `card_runtime.py` public functions or CLI
- **THEN** the same public entrypoints remain available
- **AND** I/O, ledger, envelope, single-card ACK, and bundle ACK behavior are owned by focused child modules.

#### Scenario: User-flow diagram facade remains compatible
- **WHEN** code imports or invokes the existing `flowpilot_user_flow_diagram.py` functions or CLI
- **THEN** the same public behavior remains available
- **AND** source loading, route-tree projection, stage classification, Mermaid rendering, Markdown rendering, and CLI behavior are owned by focused child modules.

### Requirement: Prompt-like packet text lives in runtime-kit prompt assets
Packet/result identity and output-contract prompt text SHALL be stored in runtime-kit prompt assets with manifest hashes instead of long inline Python literals.

#### Scenario: Packet prompt asset is loaded through PromptStore
- **WHEN** packet runtime renders packet identity, result identity, or output-contract text
- **THEN** the text is loaded from `runtime_kit/prompts/`
- **AND** the prompt manifest records the asset path, hash, and template variables.

#### Scenario: Stale or partial prompt assets are rejected
- **WHEN** a prompt asset is missing, has an unexpected hash, or uses undeclared template variables
- **THEN** PromptStore validation fails
- **AND** no unsafe inline fallback is used.

### Requirement: StructureMesh guards the final runtime split
FlowGuard StructureMesh/TestMesh evidence SHALL cover the final runtime split before the pass is called complete.

#### Scenario: Runtime split evidence is current
- **WHEN** the final runtime clarity pass is reported complete
- **THEN** StructureMesh and TestMesh checks pass for the touched runtime boundaries
- **AND** known-bad hazards for missing owners, micro-module explosion, stale parity, and insufficient evidence still fail.

#### Scenario: Public entrypoints remain allowlisted
- **WHEN** StructureMesh checks inspect public entrypoints
- **THEN** the documented router/runtime public API remains available
- **AND** private unsupported historical exports are not expanded without owner evidence.

### Requirement: Heavy regressions use hidden background evidence
Heavy FlowGuard and router regressions SHALL run through the repository background artifact contract when release-level confidence is claimed.

#### Scenario: Background router tier completes with final artifacts
- **WHEN** the router background tier is reported complete
- **THEN** stdout, stderr, combined, exit, and meta artifacts exist under `tmp/flowguard_background/`
- **AND** the meta/exit evidence shows a successful terminal status.

#### Scenario: Meta and Capability regressions are reported from final artifacts
- **WHEN** Meta or Capability regressions are reported complete
- **THEN** their background artifacts include final exit and meta evidence
- **AND** progress output alone is not treated as pass evidence.
