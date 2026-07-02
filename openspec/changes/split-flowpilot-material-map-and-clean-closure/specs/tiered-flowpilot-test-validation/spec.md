# tiered-flowpilot-test-validation Specification

## ADDED Requirements

### Requirement: Clean closure validation separates source, replay, install, and peer-work evidence

Clean FlowPilot closure validation SHALL separately prove current source
behavior, historical blocker replay coverage, installed skill freshness, and
local git scope. Peer-agent dirty files SHALL be preserved and reported instead
of reverted or silently absorbed.

#### Scenario: Historical blocker replay is supplied by peer work
- **WHEN** repair dossier or active-child-lineage changes provide historical
  blocker replay tests
- **THEN** this closure may consume their current passing evidence
- **AND** MUST NOT rewrite those peer-owned files unless the closure change
  explicitly owns the same paths.

#### Scenario: Install sync is verified
- **WHEN** repository-owned FlowPilot sources pass validation
- **THEN** install sync MUST run before local install audit
- **AND** installed self-check MUST pass against the synchronized skill.
