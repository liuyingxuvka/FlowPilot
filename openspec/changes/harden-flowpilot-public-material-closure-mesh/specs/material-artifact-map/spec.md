# material-artifact-map Specification

## ADDED Requirements

### Requirement: Material artifact map is a navigation index, not a permission allowlist

The material artifact map SHALL record safe metadata for important current-run/project artifacts without becoming the authority for what formal roles may read.

#### Scenario: Map omits a non-sealed relevant file
- **WHEN** a relevant non-sealed file exists under the current project/run roots
- **AND** the map has not indexed that file
- **THEN** PM, Worker, Reviewer, and FlowGuard Operator MAY still read the file
- **AND** the omission is an indexing/audit gap, not a read-permission blocker.

### Requirement: Map indexes important public work artifacts

The map SHALL include current known important non-sealed artifacts such as PM material understanding, high-standard/acceptance artifacts, evidence files, FlowGuard artifacts, test/log outputs, final artifacts, route/frontier/closure ledgers, and generated-resource disposition records when present.

#### Scenario: Final closure reads material map
- **WHEN** PM builds final ledger or Reviewer performs terminal replay
- **THEN** the map MUST expose navigable source refs for important non-sealed artifacts and sealed body metadata without body text.

### Requirement: Map preserves sealed body text exclusion

The map SHALL NOT read, copy, summarize, or embed sealed body text.

#### Scenario: Packet/result body appears in the map
- **WHEN** a packet or result body ref is indexed
- **THEN** its map entry MUST mark runtime open required and ordinary file read disallowed for that body ref.
