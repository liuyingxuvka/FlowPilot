## ADDED Requirements

### Requirement: Acceptance Registry Child Evidence Freshness
Router runtime TestMesh SHALL expose acceptance-registry child-suite freshness before supporting broad router confidence. It MUST distinguish current pass, stale pass, timeout, not-run, release-only deferred, and background-progress-only evidence.

#### Scenario: Child suite freshness is visible
- **WHEN** a router validation claim includes acceptance-registry behavior
- **THEN** the TestMesh evidence lists the owning child suites, result paths, freshness, timeout status, and release-scope caveats

#### Scenario: Background progress does not count as pass
- **WHEN** a child suite was launched in the background but no final exit/result artifact exists
- **THEN** the parent router TestMesh treats that child as in-progress or missing rather than passed

### Requirement: Acceptance Registry Tier Mapping
Router runtime TestMesh SHALL map acceptance-registry risks to the router-quality-gates, router-packets, router-route, router-terminal, integration, and release tiers. Each mapping MUST state whether the tier is routine, release-only, slow, background-recommended, or deferred.

#### Scenario: Tier mapping names scoped gaps
- **WHEN** not all router tiers are executed for an acceptance-registry validation claim
- **THEN** the report names which tiers were run, which were inspected by dry-run only, and which remain release-scope gaps
