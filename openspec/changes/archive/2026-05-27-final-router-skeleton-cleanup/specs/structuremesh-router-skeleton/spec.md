## MODIFIED Requirements

### Requirement: Router skeleton remains the public entrypoint
The FlowPilot router SHALL keep `skills/flowpilot/assets/flowpilot_router.py`
as the executable CLI entrypoint and supported runtime import surface while
removing the broad legacy-private compatibility contract.

#### Scenario: Public allowlist is preserved
- **WHEN** supported callers import or execute the router
- **THEN** the allowlisted CLI/runtime entrypoints MUST continue to work
- **AND** old private helpers MUST NOT be treated as documented public API.

### Requirement: Internal owner lookups are explicit and owned
Router-internal transitional helper lookups SHALL be represented by an explicit
owner-export registry or by direct owner-module imports.

#### Scenario: Legacy helper wrapper is removed
- **WHEN** a hand-written router wrapper is deleted
- **THEN** the helper MUST either be unused, directly imported from its owner,
  or mapped to one explicit owner module in the owner-export registry
- **AND** StructureMesh MUST reject missing, duplicate, or unregistered owners.

### Requirement: Router split remains behavior-preserving
The final skeleton cleanup SHALL NOT rename event names, schema values, ledger
shapes, or CLI commands.

#### Scenario: Skeleton cleanup completes
- **WHEN** focused router tests and FlowGuard checks run
- **THEN** public CLI/runtime behavior MUST remain compatible
- **AND** validation evidence MUST cover the skeleton public surface and
  internal owner-export surface separately.

### Requirement: Local completion includes install and evidence
FlowPilot maintenance SHALL finish with local install synchronization, local
repository validation, and local Git versioning. Remote publication remains
deferred.

#### Scenario: Local maintenance pass is complete
- **WHEN** the skeleton cleanup and validation pass complete
- **THEN** the installed local FlowPilot skill MUST be source-fresh
- **AND** the work MUST be committed locally
- **AND** no GitHub push, tag, or remote release publication SHALL occur.
