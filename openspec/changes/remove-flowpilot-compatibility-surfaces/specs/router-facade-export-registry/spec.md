## ADDED Requirements

### Requirement: Public Router Exports Are Current Owner APIs
FlowPilot router export registries SHALL expose current owner APIs and SHALL
NOT require compatibility facade exports as release or install surfaces.

#### Scenario: Current owner API is imported
- **WHEN** repository code imports a current owner module API
- **THEN** the import resolves without requiring compatibility facade
  re-exports

#### Scenario: Compatibility facade export remains
- **WHEN** an export exists only to preserve an old module boundary
- **THEN** the export is removed or classified as a staged StructureMesh
  contraction item
- **AND** final release confidence SHALL NOT count that export as current owner
  behavior
