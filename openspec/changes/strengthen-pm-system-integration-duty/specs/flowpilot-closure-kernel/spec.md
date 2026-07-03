## ADDED Requirements

### Requirement: Parent closure consumes composition evidence
FlowPilot SHALL require parent closure to verify that effective child outputs compose into the parent goal.

#### Scenario: Parent pass requires composition
- **WHEN** a parent/module node is reviewed after child completion
- **THEN** the review SHALL confirm that child outputs are usable together, ordered correctly, non-duplicative unless justified, and sufficient for the parent goal.

#### Scenario: Local child pass does not imply parent pass
- **WHEN** every child has local evidence but the parent artifact is incomplete, scattered, or missing required bridges
- **THEN** the parent SHALL remain unresolved until PM chooses an existing repair, sibling insertion, subtree rebuild, bubble-up, or stop decision.

### Requirement: Terminal closure consumes whole-output evidence
FlowPilot SHALL require final closure to review the delivered output as a coherent whole.

#### Scenario: Final ledger includes whole-output composition review
- **WHEN** PM builds the final route-wide gate ledger
- **THEN** it SHALL include a whole-output composition review that is separate from node-by-node evidence collection.

#### Scenario: Final reviewer starts from user-facing artifact
- **WHEN** Reviewer performs final backward replay
- **THEN** Reviewer SHALL begin from the delivered product or final output and then trace back to route nodes, parent nodes, and evidence.

#### Scenario: Scattered final output routes to existing closure repair
- **WHEN** final replay finds a hard scattered-output failure
- **THEN** PM SHALL use existing terminal repair, route mutation, model-miss, or PM-stop paths instead of treating the output as passed because every node has a report.
