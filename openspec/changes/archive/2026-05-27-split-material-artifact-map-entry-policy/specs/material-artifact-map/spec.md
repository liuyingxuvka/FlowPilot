## MODIFIED Requirements

### Requirement: Run-scoped material artifact map
FlowPilot SHALL maintain a run-scoped material artifact map that indexes reusable material, research, modeling, self-interrogation, PM package, reviewer, and generated-resource artifacts using safe metadata rather than sealed body content.

#### Scenario: Material map entry policy is internally split without changing output
- **WHEN** FlowPilot refreshes the material artifact map after the entry policy has been moved into a child module
- **THEN** the public material-map facade still writes the same schema, safe source refs, hashes, statuses, access boundaries, review source entry ids, and reviewable source paths as before
- **AND** the child entry-policy module MUST NOT import the public facade or become a second authority surface
