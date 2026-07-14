# material-artifact-map Specification

## Purpose
TBD - created by archiving change add-material-artifact-map. Update Purpose after archive.
## Requirements
### Requirement: Run-scoped material artifact map
FlowPilot MAY maintain a run-scoped material artifact map when PM determines that reusable navigation materially helps a long project. When present, it SHALL index reusable material, research, modeling, self-interrogation, PM package, Reviewer, and generated-resource artifacts using safe metadata rather than sealed body content; its absence SHALL NOT block the current route.

#### Scenario: Material map entry policy is internally split without changing output
- **WHEN** FlowPilot refreshes an optional material artifact map after the entry policy has been moved into a child module
- **THEN** the public material-map facade still writes the same schema, safe source refs, hashes, statuses, access boundaries, review source entry ids, and reviewable source paths as before
- **AND** the child entry-policy module MUST NOT import the public facade or become a second authority surface.

#### Scenario: Optional map is absent
- **WHEN** PM does not need a reusable material navigation index
- **THEN** FlowPilot SHALL NOT create a mandatory map task, blocker, gate, or completion obligation.

### Requirement: Existing authority remains authoritative
The material artifact map SHALL be an index and navigation aid only; it MUST NOT become a gate approval, role decision, Controller evidence source, or substitute for PM/reviewer/runtime ledgers.

#### Scenario: PM uses map for route context
- **WHEN** PM reviews route memory or prior-path context before a route, repair, resume, final-ledger, or closure decision
- **THEN** PM may use the material artifact map to locate source artifacts, but PM MUST cite and inspect the underlying source paths required by the active decision contract

#### Scenario: Controller sees safe metadata only
- **WHEN** Controller loads route memory, action metadata, or the material artifact map
- **THEN** Controller sees only safe metadata and MUST NOT read, execute, summarize, or repair sealed packet/result bodies

### Requirement: Packet-authorized worker material reads
PM-authored worker and research packets MAY declare material artifact map entries as allowed reads, and workers SHALL use only those declared entries inside the opened packet boundary.

#### Scenario: Worker receives allowed map entries
- **WHEN** a worker opens a PM-authored packet that declares `allowed_material_map_entry_ids`
- **THEN** the worker may inspect those map entries and their non-sealed source paths as part of the packet's allowed reads

#### Scenario: Worker lacks sealed-body runtime authority
- **WHEN** an allowed map entry points to a sealed body that requires runtime opening and the worker does not have runtime authority for that body
- **THEN** the worker MUST report `needs_pm` or a blocker instead of reading the sealed body through ordinary filesystem access

### Requirement: Route memory and final ledger link the map
Route memory and final route-wide ledger artifacts SHALL link the material artifact map only when it exists and is actually used as navigation for current evidence; they SHALL NOT require map creation or duplicate sealed content.

#### Scenario: Route memory references existing map
- **WHEN** FlowPilot refreshes route memory and an optional material artifact map exists
- **THEN** route memory MAY cite the map path and SHALL state that the map is not acceptance evidence by itself.

#### Scenario: Final ledger has no map
- **WHEN** no material artifact map was created
- **THEN** final closure SHALL judge the underlying required artifacts and evidence directly and SHALL NOT report a missing-map gap.

