## ADDED Requirements

### Requirement: Progress display is cumulative and monotonic

FlowPilot SHALL present route progress as a cumulative display projection that
does not make earlier completed setup, route-expansion, formal work, repair, or
reopened work disappear from the visible denominator.

#### Scenario: Formal route expands after setup work
- **WHEN** FlowPilot has already displayed setup or pre-route progress
- **AND** PM later activates a formal route with additional nodes
- **THEN** the display projection MUST preserve the earlier displayed work and
  append the formal nodes instead of replacing the total with only the new route
  nodes

#### Scenario: Repair reopens or supplements completed work
- **WHEN** a completed or accepted node later requires repair, reopened review,
  or supplemental work
- **THEN** FlowPilot MUST append repair or reopened work to the display
  projection rather than decreasing the completed count or total node count

### Requirement: Display progress remains non-authoritative

FlowPilot SHALL keep route/frontier files, not display progress, as execution
authority.

#### Scenario: Display and frontier disagree
- **WHEN** the cumulative progress display disagrees with current route or
  frontier authority
- **THEN** runtime MUST refresh or mark the display stale and MUST NOT advance
  execution from the display projection alone
