## ADDED Requirements

### Requirement: Diagnostics Feed Model Maturation Actions
FlowPilot model-test-code diagnostics SHALL convert missing, stale, overclaimed, duplicate-primary, boundary-mismatch, and progress-only findings into model maturation signals.

#### Scenario: Diagnostic stale row becomes refresh action
- **WHEN** a diagnostic row says evidence is stale for a model obligation or code boundary
- **THEN** the maturation gate emits `refresh_evidence` for the affected model or boundary

#### Scenario: Duplicate primary edge becomes split action
- **WHEN** multiple primary evidence rows claim the same model obligation edge path
- **THEN** the maturation gate emits a split or child-model action rather than silently downgrading one evidence row

### Requirement: Diagnostics Preserve Scoped Confidence
FlowPilot SHALL preserve scoped confidence when diagnostics find unresolved model-test-code gaps that do not block all local development.

#### Scenario: Gap remains open after focused repair
- **WHEN** a diagnostic gap remains open but is outside the current focused repair boundary
- **THEN** FlowPilot records the scoped gap and avoids claiming full confidence for the broader surface
