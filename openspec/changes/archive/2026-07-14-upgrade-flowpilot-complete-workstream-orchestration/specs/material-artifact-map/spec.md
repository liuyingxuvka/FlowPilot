## MODIFIED Requirements

### Requirement: Run-scoped material artifact map
FlowPilot MAY maintain a run-scoped material artifact map when PM determines that reusable navigation materially helps a long project. When present, it SHALL index reusable material, research, modeling, self-interrogation, PM package, Reviewer, and generated-resource artifacts using safe metadata rather than sealed body content; its absence SHALL NOT block the current route.

#### Scenario: Material map entry policy is internally split without changing output
- **WHEN** FlowPilot refreshes an optional material artifact map after the entry policy has been moved into a child module
- **THEN** the public material-map facade still writes the same schema, safe source refs, hashes, statuses, access boundaries, review source entry ids, and reviewable source paths as before
- **AND** the child entry-policy module MUST NOT import the public facade or become a second authority surface.

#### Scenario: Optional map is absent
- **WHEN** PM does not need a reusable material navigation index
- **THEN** FlowPilot SHALL NOT create a mandatory map task, blocker, gate, or completion obligation.

### Requirement: Route memory and final ledger link the map
Route memory and final route-wide ledger artifacts SHALL link the material artifact map only when it exists and is actually used as navigation for current evidence; they SHALL NOT require map creation or duplicate sealed content.

#### Scenario: Route memory references existing map
- **WHEN** FlowPilot refreshes route memory and an optional material artifact map exists
- **THEN** route memory MAY cite the map path and SHALL state that the map is not acceptance evidence by itself.

#### Scenario: Final ledger has no map
- **WHEN** no material artifact map was created
- **THEN** final closure SHALL judge the underlying required artifacts and evidence directly and SHALL NOT report a missing-map gap.

## REMOVED Requirements

### Requirement: Reviewer material sufficiency uses concrete source refs
**Reason**: A mandatory dedicated material-sufficiency gate makes material processing a special startup workflow even when PM can read current material directly or request ordinary bounded evidence work.

**Migration**: Use direct PM reading or an existing ordinary PM role-work packet; when source quality is material to a dependent decision, Reviewer inspects concrete source refs through that ordinary package's existing review contract.
