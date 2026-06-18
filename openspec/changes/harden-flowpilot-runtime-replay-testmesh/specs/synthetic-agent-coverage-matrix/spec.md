## ADDED Requirements

### Requirement: Synthetic matrix separates generated cells from runtime replayed cells
FlowPilot SHALL distinguish fake-AI cells that are merely generated from cells
that have executable runtime replay evidence. Broad high-risk coverage SHALL
require runtime replay evidence for selected contract, review-window, retry,
and break-glass cells.

#### Scenario: Generated-only cell is not replay proof
- **WHEN** a fake-AI cell exists only as a generated payload or matrix row
- **THEN** the coverage report MUST preserve that boundary and MUST NOT count
  it as runtime recovery evidence.

#### Scenario: Runtime replayed cell proves control-plane reaction
- **WHEN** a fake-AI cell is submitted through the runtime replay harness and
  produces the expected reject, reissue, repair, acceptance, or break-glass
  result
- **THEN** the coverage report MAY mark that cell as runtime-replayed
  non-live control-plane evidence.

### Requirement: Real issue backfeed rows join the synthetic coverage matrix
FlowPilot SHALL require every registered real-run anomaly that remains in scope
to have a durable synthetic coverage row linking source evidence, fake-AI
profile, contract cell, Cartesian row, and expected runtime reaction.

#### Scenario: Real issue lacks synthetic backfeed
- **WHEN** a real-run anomaly is registered without a fake-AI profile, contract
  cell, Cartesian row, or runtime replay expectation
- **THEN** the synthetic coverage matrix MUST report the anomaly as an open
  backfeed gap.
