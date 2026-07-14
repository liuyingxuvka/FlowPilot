# finite-ai-contract-exhaustion Specification

## Purpose
TBD - created by archiving change upgrade-flowpilot-complete-workstream-orchestration. Update Purpose after archive.
## Requirements
### Requirement: One canonical fake responder owns semantic profiles
FlowPilot SHALL generate all new synthetic AI responses through `ContractDrivenFakeAIResponder.from_open_packet_result` after opening the real current packet and SHALL NOT introduce a second fake response family or bypass real submit/review paths.

#### Scenario: Semantic fake profile executes
- **WHEN** a complete-plan, shallow-plan, incomplete-plan, stale-evidence, delegation-gap, FlowGuard-self-approval, material-work, or skill-selection profile is selected
- **THEN** the canonical responder SHALL build the profile from the current open-packet contract
- **AND** Runtime, PM disposition, FlowGuard, Reviewer, repair, and retry SHALL consume it through their real current-contract APIs.

### Requirement: Coverage accounting separates every evidence state
The finite coverage mesh SHALL separately report declared, applicable, excluded, generated, selected, executed, passed, failed, stale, and proof-backed cases and SHALL preserve the ids and reasons needed to reconcile those sets.

#### Scenario: Generated case was not executed
- **WHEN** a case exists in the generator but no current execution artifact proves it ran
- **THEN** the case MAY count as generated or selected
- **AND** SHALL NOT count as executed, passed, or proof-backed.

#### Scenario: Child proof is stale
- **WHEN** a parent receipt references a child artifact whose source fingerprint is stale
- **THEN** the parent SHALL classify those cases as stale and SHALL NOT preserve their prior proof-backed count.

### Requirement: Finite universes use layered interaction strength
FlowPilot SHALL fully enumerate declared finite static contract values, execute every single-axis mutation at its real owner, cover public-path pairs, add named high-risk triples and selected four-way combinations, and keep historical misses, bounded fuzz, fake projects, and live-AI samples as separate evidence classes.

#### Scenario: Pairwise public-path coverage is selected
- **WHEN** multiple finite axes interact through a public FlowPilot path
- **THEN** the mesh SHALL generate deterministic pairwise cases plus the declared high-risk higher-order combinations
- **AND** SHALL identify excluded combinations with reasons.

### Requirement: Coverage claims remain bounded
FlowPilot SHALL describe synthetic and Cartesian evidence only as proof of the declared finite contract/control-flow universe and SHALL NOT claim exhaustive natural-language quality, arbitrary AI behavior, or future model correctness.

#### Scenario: All declared cases pass
- **WHEN** every applicable declared finite case has current proof-backed pass evidence
- **THEN** FlowPilot MAY claim that declared universe is closed
- **AND** SHALL retain the live-AI and arbitrary-language claim boundary.

