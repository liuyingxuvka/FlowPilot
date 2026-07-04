## ADDED Requirements

### Requirement: Final ledger closes source intent against the delivered product
FlowPilot SHALL require PM final ledger and closure prompts to close active
acceptance items by tracing from the delivered product or final output back to
source requirements and current evidence, not by process completion alone.

#### Scenario: PM final ledger maps source to delivered artifact
- **WHEN** PM builds the final route-wide gate ledger
- **THEN** PM SHALL identify how each active user-sourced or PM high-standard
  acceptance item is closed, waived, superseded, or blocked against current
  delivered artifacts and direct evidence
- **AND** PM SHALL keep unresolved, stale, report-only, or existence-only rows
  visible as blockers.

### Requirement: Terminal backward replay starts from final output
FlowPilot SHALL require terminal backward replay prompts to begin with the
actual delivered output and replay backward through root acceptance, effective
route nodes, child-skill standards, evidence quality, and repair decisions.

#### Scenario: Final output drift blocks terminal replay
- **WHEN** the delivered output has drifted from accepted source requirements,
  node outputs, selected child-skill standards, or prior accepted artifacts
- **THEN** Reviewer SHALL block terminal replay or require PM repair
- **AND** terminal replay SHALL NOT pass only because earlier stages passed.

#### Scenario: Ledger-only replay is insufficient
- **WHEN** terminal replay can inspect only clean ledgers or process records but
  lacks direct basis to judge delivered-output satisfaction
- **THEN** Reviewer SHALL block, request evidence, or scope the claim instead
  of approving closure.
