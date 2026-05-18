## ADDED Requirements

### Requirement: Prioritized full diagnostic findings
The model-test-code diagnostic SHALL attach actionable triage metadata to each
finding, including severity, surface owner, release relevance, repair type,
dedupe key, and a prioritized top-findings view.

#### Scenario: Diagnostic emits repair metadata
- **WHEN** the full FlowPilot model-test-code diagnostic is generated
- **THEN** every finding includes severity, surface owner, release relevance,
  repair type, and dedupe key fields

#### Scenario: Duplicate findings are grouped
- **WHEN** several findings point to the same owner surface and repair class
- **THEN** the diagnostic exposes a deduplicated actionable summary instead of
  requiring maintainers to inspect every raw row manually

### Requirement: External contract evidence coverage
The diagnostic SHALL distinguish external-contract tests from internal-only
tests for model-owned code surfaces and SHALL recognize facade parity and public
script entrypoint tests as external-contract evidence.

#### Scenario: Facade parity counts as source contract evidence
- **WHEN** a facade exports owner-module symbols and a test verifies that public
  facade contract against the owner implementations
- **THEN** the diagnostic marks that facade surface as externally covered rather
  than internal-only

#### Scenario: Internal-only tests remain visible
- **WHEN** tests exercise implementation helpers without checking the owner
  module's public input/output contract
- **THEN** the diagnostic reports internal-only evidence instead of treating it
  as full external-contract coverage

### Requirement: CLI entrypoint behavior coverage
The repository SHALL include fast tests for public FlowPilot script entrypoints
that verify safe observable behavior without running long regressions.

#### Scenario: Public CLI smoke tests are fast
- **WHEN** installer, local-sync, release-audit, test-tier, packet, output, and
  lifecycle entrypoints are tested
- **THEN** the tests use help, list, dry-run, check, or local-only audit modes
  and do not require long-running model simulations

#### Scenario: Test-tier public options remain parseable
- **WHEN** the test-tier runner is invoked through list, dry-run, child, or
  supervisor public option paths
- **THEN** the command returns a stable machine-readable or parseable result
  that can be used as CLI contract evidence

### Requirement: Background evidence classification
The diagnostic SHALL classify background validation artifacts using final meta
and exit evidence, including BOM-tolerant meta reads, and SHALL distinguish
pass, failed, running, incomplete, stale, progress-only, and local-only release
proof states.

#### Scenario: Progress-only evidence does not pass
- **WHEN** a background run has progress output but lacks final meta or exit
  artifacts
- **THEN** the diagnostic reports progress-only or incomplete evidence rather
  than pass

#### Scenario: Local-only release proof is explicit
- **WHEN** release validation uses a URL-skip mode such as `--skip-url-check`
- **THEN** the diagnostic reports the evidence as local-only proof rather than
  public release proof

### Requirement: Structure split repair planning
The diagnostic SHALL report oversized or multi-owner modules as structure-split
repair candidates and SHALL identify whether each split is immediate or
deferred with a concrete reason.

#### Scenario: Deferred split remains actionable
- **WHEN** a module needs further splitting but broad edits would risk colliding
  with fresh owner-module polish or peer work
- **THEN** the diagnostic records the owner, candidate surface, repair type, and
  deferral reason without claiming the structure repair is complete
