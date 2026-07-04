## ADDED Requirements

### Requirement: Pointer/body hardening obligations bind to tests and alignment
FlowPilot SHALL bind pointer persistence and body-entry hardening obligations
to current ordinary tests, ContractExhaustionMesh shards, TestMesh ownership,
and Model-Test Alignment rows before claiming broad completion.

#### Scenario: Model obligation has owner code and tests
- **WHEN** a model obligation is created for pointer atomic writes, pointer
  recovery, ambiguous recovery blocking, or body-entry rejection
- **THEN** it MUST name the owner code surface and current ordinary test
  evidence that exercises the public or external contract boundary.

#### Scenario: ContractExhaustionMesh shard is consumed
- **WHEN** ContractExhaustionMesh generates pointer or body-entry cases
- **THEN** TestMesh and Model-Test Alignment MUST consume those case or shard
  ids before the parent coverage claim can be treated as current.

#### Scenario: Prompt/card coverage is aligned
- **WHEN** prompt/card return policy changes
- **THEN** card instruction coverage and install checks MUST prove the
  generated cards match the new `--body-file` default before installed-skill
  synchronization is treated as current.
