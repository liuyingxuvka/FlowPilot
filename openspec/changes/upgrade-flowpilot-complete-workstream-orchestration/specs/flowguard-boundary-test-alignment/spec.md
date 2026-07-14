## ADDED Requirements

### Requirement: Complete-workstream obligations align model, source, and tests
FlowPilot SHALL map each complete-workstream lifecycle step, report-plan audit, PM integration duty, Reviewer challenge, and FlowGuard self-approval boundary to one primary FlowGuard obligation owner, one source contract, and current ordinary test evidence.

#### Scenario: Plan-report obligation lacks ordinary evidence
- **WHEN** Model-Test Alignment finds a complete-workstream obligation with only prompt text or generated model evidence
- **THEN** the alignment gate SHALL fail until an ordinary test exercises the current role/report/review path.

### Requirement: Material contraction aligns positive and negative evidence
FlowPilot SHALL map retained skill discovery, ordinary material work packets, optional material-map behavior, and every removed material-special surface to current source and test evidence.

#### Scenario: Removed material field remains positive
- **WHEN** `material_sources` or `material_sufficiency` remains in a successful current discovery skeleton, prompt contract, fake response, runtime fallback read, or positive model obligation
- **THEN** the alignment gate SHALL fail and classify the hit for deletion rather than compatibility support.

#### Scenario: Historical material label remains
- **WHEN** an old material name appears only in a forbidden/deleted-field registry, negative test, or clearly historical evidence label
- **THEN** alignment MAY retain the hit with that explicit disposition.
