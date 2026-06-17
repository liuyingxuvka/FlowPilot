## ADDED Requirements

### Requirement: Break-glass counts repeated repair lineage attempts
FlowPilot SHALL count repeated same-problem repair attempts across replacement
node lineage so canonical no-in-place repair cannot hide a repair loop behind
new physical node ids.

#### Scenario: Same lineage repeats same blocker class
- **WHEN** repair nodes such as `package-repair-v2`, `package-repair-v3`, and `package-repair-v4` repeat the same blocker class, gate kind, and required recheck role
- **THEN** Runtime MUST normalize them to the same repair lineage root for break-glass threshold counting
- **AND** superseded repair-chain blocker rows MUST remain usable as loop evidence even though they are not current status blockers.

#### Scenario: Different lineage does not trigger same counter
- **WHEN** similar blocker classes occur on unrelated route node lineages
- **THEN** Runtime MUST keep them in ordinary PM/reviewer repair handling
- **AND** Runtime MUST NOT trigger same-lineage break-glass from cross-node similarity alone.

#### Scenario: Threshold blocks another ordinary repair
- **WHEN** the same lineage exceeds the configured repeated same-problem threshold
- **THEN** Runtime MUST stop issuing another ordinary repair packet for that lineage/problem identity
- **AND** Runtime MUST route the condition to Controller break-glass diagnosis or a terminal stop path.
