## ADDED Requirements

### Requirement: Thin Parents Prefer Canonical Child Evidence
FlowPilot thin-parent and hierarchy evidence selectors SHALL prefer canonical current
child result artifacts over shadow check-named artifacts when both exist for the same
model family.

#### Scenario: Two child result names share a family
- **WHEN** `family_results.json` and `family_checks_results.json` are both present
  for the same child model family
- **THEN** thin-parent and hierarchy evidence rows use `family_results.json`
- **AND** shadow check-named files cannot keep stale compatibility semantics alive.
