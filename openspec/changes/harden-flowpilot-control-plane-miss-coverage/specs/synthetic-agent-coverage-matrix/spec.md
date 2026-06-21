## ADDED Requirements

### Requirement: Synthetic matrix covers observed miss families by same-class Cartesian cells

FlowPilot SHALL convert every live control-plane miss that appears after a
coverage claim into a model-scoped synthetic-agent coverage family with finite
axes, generated case ids, an oracle, and a current evidence owner.

#### Scenario: Live miss backfeeds a generated coverage family
- **WHEN** a live run exposes a reviewer identity, review completeness,
  acceptance projection, formal attachment, final closure, progress display, or
  break-glass routing miss
- **THEN** the synthetic coverage matrix MUST add same-class generated cells for
  that miss family
- **AND** each generated cell MUST identify whether the expected outcome is
  pass, reject, reissue, normal repair, or threshold break-glass

#### Scenario: Hand-picked examples cannot support full coverage
- **WHEN** a miss family is represented only by one or more hand-written example
  tests
- **THEN** FlowPilot MUST classify the family as seeded but not full coverage
  until the finite axes, cells, or scoped exclusions are declared

### Requirement: Fake-AI rehearsal covers empty, partial, extra, malformed, and complete projections

FlowPilot SHALL rehearse current fake-AI results for finite projection surfaces,
including empty owner sets, partial owner sets, extra ids, malformed rows, and
complete valid rows.

#### Scenario: Empty owner set rejects invented projection ids
- **WHEN** a fake-AI node-context result references acceptance item ids outside
  an empty owner set
- **THEN** runtime MUST reject or reissue with feedback naming the allowed empty
  set and the offending ids

#### Scenario: Complete projection passes without repair
- **WHEN** fake-AI returns a projection that exactly matches the current owner
  set and row-shape contract
- **THEN** runtime MUST accept it without creating a control blocker or
  break-glass incident

### Requirement: Coverage matrix includes repeated-failure threshold cells

FlowPilot SHALL test both normal repeated-repair behavior and the dedicated
break-glass fuse for each same-class mechanical blocker family.

#### Scenario: Repeats before threshold stay normal
- **WHEN** the same repairable blocker class repeats fewer times than the
  configured break-glass threshold
- **THEN** fake-AI rehearsal MUST show a normal reject, reissue, or PM repair
  path and MUST NOT open break-glass

#### Scenario: Threshold repeat opens break-glass
- **WHEN** the same root-cause blocker reaches the configured break-glass
  threshold
- **THEN** fake-AI rehearsal MUST show break-glass opens with the repeated
  root-cause lineage recorded
