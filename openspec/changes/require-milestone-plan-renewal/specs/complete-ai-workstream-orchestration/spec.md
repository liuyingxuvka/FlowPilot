## ADDED Requirements

### Requirement: PM renews the long-project route after every major milestone
PM SHALL treat accepted top-level milestones as new planning evidence. Before
FlowPilot continues, PM SHALL reconstruct current project state, audit
completed work, deviations and unclosed goal gaps, consult the prior remaining
plan as context, and submit a fresh complete remaining route to the final user
goal.

#### Scenario: New evidence confirms the prior route
- **WHEN** the completed milestone adds evidence but does not change the best
  remaining route
- **THEN** PM SHALL still rewrite and justify the complete remaining route
- **AND** SHALL NOT treat the initial planning result as self-renewing
  authority.

#### Scenario: New evidence exposes a plan defect
- **WHEN** the completed milestone exposes a false assumption, omitted
  dependency, changed constraint, or deeper necessary step
- **THEN** PM SHALL incorporate that evidence into the new remaining route
- **AND** SHALL preserve the final goal rather than optimizing for the stale
  plan.

#### Scenario: PM submits only the next action
- **WHEN** PM submits a next task or local repair without a route spanning all
  remaining work to the final goal
- **THEN** the milestone renewal SHALL remain incomplete.
