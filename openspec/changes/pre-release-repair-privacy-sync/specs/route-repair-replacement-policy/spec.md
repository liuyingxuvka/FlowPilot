## ADDED Requirements

### Requirement: Route mutation policies declare replacement topology
FlowPilot SHALL require every structural route mutation to name an explicit
topology strategy before the replacement route can activate.

#### Scenario: Return repair names original return target
- **WHEN** PM chooses a return-to-original repair strategy
- **THEN** the mutation record names the original return node and records that
  the repair work must rejoin that node after repair evidence and replay pass.

#### Scenario: Supersede original names replacement and superseded nodes
- **WHEN** PM chooses to replace an original node instead of returning to it
- **THEN** the mutation record names the replacement node and every superseded
  original node before Router can activate the replacement frontier.

#### Scenario: Sibling branch replacement names affected siblings
- **WHEN** PM chooses to replace a sibling branch or module
- **THEN** the mutation record names the replacement branch root, the affected
  sibling nodes, and the ancestor scope that must be replayed.

### Requirement: Replacement activation invalidates stale evidence
FlowPilot SHALL mark affected prior evidence as stale, superseded, quarantined,
or context-only before a mutated route branch can provide current proof.

#### Scenario: Old sibling evidence cannot close new branch
- **WHEN** a sibling branch is superseded by a replacement branch
- **THEN** prior proof from the superseded sibling is not accepted as current
  evidence for the replacement branch or final route-wide ledger.

#### Scenario: Replacement activation blocks without stale ledger
- **WHEN** PM proposes a replacement route but omits stale evidence disposition
- **THEN** Router blocks activation and leaves the route mutation pending for a
  corrected PM decision.

### Requirement: Replacement frontier requires replay before completion
FlowPilot SHALL rewrite the execution frontier to the replacement node and
require same-scope replay before route completion can proceed.

#### Scenario: Frontier enters replacement branch
- **WHEN** replacement topology and stale-evidence disposition are valid
- **THEN** Router rewrites the execution frontier to the replacement branch or
  repair node rather than continuing from the superseded node.

#### Scenario: Final ledger waits for replay after mutation
- **WHEN** a route mutation has activated but same-scope replay has not passed
- **THEN** final route-wide ledger and terminal closure remain blocked.

### Requirement: Repair replacement evidence is modeled before runtime edits
FlowPilot SHALL keep focused FlowGuard evidence for route repair/replacement
policy before relying on runtime changes.

#### Scenario: Known-bad replacement hazards fail
- **WHEN** the focused model mutates away topology strategy, stale evidence
  invalidation, frontier rewrite, same-scope replay, or final-ledger blocking
- **THEN** the model reports the corresponding unsafe state as a detected
  hazard before the runtime change is trusted.

#### Scenario: Heavy models can be explicitly skipped
- **WHEN** a maintenance pass touches only the focused route repair/replacement
  boundary and the user excludes Meta and Capability regressions
- **THEN** the final evidence names those heavy model boundaries as skipped
  with residual risk instead of reporting them as passed.
