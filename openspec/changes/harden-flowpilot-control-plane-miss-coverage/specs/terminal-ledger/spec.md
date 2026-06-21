## ADDED Requirements

### Requirement: Terminal closure repairs all closure evidence gaps through current packets

FlowPilot SHALL map terminal closure evidence gaps to current normal repair
packets before declaring closure blocked or invoking break-glass.

#### Scenario: Closure misses node acceptance plan
- **WHEN** terminal closure finds a current effective node without a required
  node acceptance plan
- **THEN** runtime MUST expose a current normal repair action that can obtain or
  reissue that node acceptance plan

#### Scenario: Closure misses terminal backward replay
- **WHEN** terminal closure finds no current terminal backward replay evidence
- **THEN** runtime MUST expose a current normal repair action that can obtain or
  reissue terminal replay before PM completion approval

#### Scenario: Closure misses route-wide gate ledger
- **WHEN** terminal closure finds an unresolved or absent final route-wide gate
  ledger
- **THEN** runtime MUST expose a current normal repair action that can rebuild
  or reissue the ledger rather than treating the absence as completed evidence

### Requirement: Terminal closure tests cover blocker combinations

FlowPilot SHALL test combinations of final-closure evidence gaps, not only one
gap at a time.

#### Scenario: Multiple closure gaps repair together
- **WHEN** terminal closure detects a combination of node acceptance,
  node-context, route-wide ledger, requirement matrix, and terminal replay gaps
- **THEN** the closure test matrix MUST verify that each gap receives a normal
  current repair action or a scoped blocker reason
