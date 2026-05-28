## ADDED Requirements

### Requirement: Registry Text Distinguishes Owner Authority From Compatibility Exports
FlowPilot registry and derived-view documentation SHALL distinguish canonical
owner authority from compatibility exports or facade names.

#### Scenario: Compatibility export is retained
- **WHEN** a registry, manifest, or derived-view map retains an older public name for compatibility
- **THEN** the surrounding text or validation evidence SHALL identify the current owner registry or derived source as the authority

#### Scenario: Canonical owner changes behavior
- **WHEN** runtime behavior depends on a registry row, policy map, or derived view
- **THEN** compatibility exports SHALL NOT be described as independent behavior owners

### Requirement: Registry Residue Has Focused Validation
FlowPilot SHALL validate any prompt/structure cleanup that changes registry,
manifest, or derived-view wording with a focused check for owner/export drift.

#### Scenario: Cleanup touches registry-owned structure
- **WHEN** cleanup edits a registry, manifest, derived-view map, or facade export table
- **THEN** focused validation SHALL prove the owner-derived view still matches the expected compatibility surface
