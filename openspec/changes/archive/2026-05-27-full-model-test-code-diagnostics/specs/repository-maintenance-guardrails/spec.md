## ADDED Requirements

### Requirement: Full diagnostic evidence is distinguished from subset alignment

Repository maintenance evidence SHALL distinguish a selected model-test
alignment pass from a full model-test-code diagnostic pass.

#### Scenario: Subset alignment is not reported as full diagnostic coverage
- **WHEN** only selected model obligations have model-test-code source audit
  evidence
- **THEN** maintenance reports the covered subset and the remaining diagnostic
  scope
- **AND** it does not claim that every owner module, facade, script entrypoint,
  and test tier is fully covered.

#### Scenario: Full diagnostic report names residual gaps
- **WHEN** the full diagnostic pass completes with uncovered surfaces
- **THEN** maintenance reports the residual gap counts and representative paths
- **AND** uncovered surfaces are not described as passed checks.

### Requirement: Background evidence remains artifact-complete

Repository maintenance evidence SHALL reject background validation evidence
that only proves liveness or progress.

#### Scenario: Progress-only background artifact is rejected
- **WHEN** a background validation surface has stdout or progress lines but no
  successful exit and meta artifact
- **THEN** maintenance records the surface as incomplete or stale
- **AND** the result cannot be used as release-quality pass evidence.
