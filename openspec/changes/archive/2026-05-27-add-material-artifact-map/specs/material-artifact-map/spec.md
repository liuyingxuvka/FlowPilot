## ADDED Requirements

### Requirement: Run-scoped material artifact map
FlowPilot SHALL maintain a run-scoped material artifact map that indexes reusable material, research, modeling, self-interrogation, PM package, reviewer, and generated-resource artifacts using safe metadata rather than sealed body content.

#### Scenario: Material map is written from existing artifacts
- **WHEN** FlowPilot writes material scan packets, PM package dispositions, reviewer material reports, research package outputs, PM material understanding, route memory, or final ledger artifacts
- **THEN** the current run includes a material artifact map with entries that cite source paths, hashes, producer roles, owner roles, statuses, authority levels, and access boundaries

#### Scenario: Map excludes sealed body content
- **WHEN** a map entry refers to a packet body or result body whose visibility is sealed
- **THEN** the map MUST cite only paths, hashes, envelope refs, runtime-open requirements, and safe summaries, and MUST NOT copy packet body text or result body text

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

### Requirement: Reviewer material sufficiency uses concrete source refs
Reviewer material sufficiency SHALL be based on the PM formal package, material artifact map refs, direct source paths, and packet-runtime audit evidence rather than raw Controller summaries or uncited worker prose.

#### Scenario: PM formal package releases reviewable refs
- **WHEN** PM absorbs material scan results and releases a formal material sufficiency package
- **THEN** the package cites the material artifact map path, review source entry ids, reviewable source paths, result envelope refs, and sealed-body boundary facts without including raw worker result bodies

#### Scenario: Reviewer direct-source claim requires paths
- **WHEN** reviewer material sufficiency reports `direct_material_sources_checked=true`
- **THEN** the report MUST include non-empty `checked_source_paths` or runtime-open receipt refs that identify the sources actually checked

#### Scenario: Reviewer cannot pass from map summary alone
- **WHEN** the reviewer has only a material-map safe summary or Controller route-memory summary and no checkable source path or runtime-open receipt
- **THEN** the reviewer MUST block or mark the material insufficient

### Requirement: Route memory and final ledger link the map
Route memory and final route-wide ledger artifacts SHALL link the material artifact map and summarize current, stale, blocked, and unresolved material-map counts without duplicating sealed content.

#### Scenario: Route memory references map
- **WHEN** FlowPilot refreshes route memory after material, research, reviewer, model, or generated-resource changes
- **THEN** `route_history_index.json` and `pm_prior_path_context.json` cite the material artifact map path when it exists and state that the map is not acceptance evidence by itself

#### Scenario: Final ledger includes material map disposition
- **WHEN** FlowPilot builds the final route-wide gate ledger
- **THEN** the ledger cites the material artifact map when present and rejects unresolved or stale current-material entries that are used as completion evidence
