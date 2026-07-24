## ADDED Requirements

### Requirement: Exact owner proof survives reference normalization
Replacing copied validation bodies with V5 references SHALL preserve each
owner's exact command, covered inputs, dependencies, environment, obligations,
evidence subjects, terminal result, cleanup proof, result fingerprint, and
current reuse-ticket identity.  Missing, mismatched, duplicate, or foreign
owner references SHALL block the parent claim.

#### Scenario: Owner index is complete
- **WHEN** a parent TestMesh consumes a V5 owner index
- **THEN** every frozen owner id resolves to exactly one current immutable proof reference with matching hash and identity
- **AND** parent execution and reuse counts equal the frozen impact plan

#### Scenario: Referenced proof is missing
- **WHEN** an owner-index row points to a missing artifact or a hash-mismatched proof
- **THEN** the owner and every consuming parent remain blocked
- **AND** another owner's proof or an aggregate pass cannot substitute for it

### Requirement: Failure diagnostics are bounded but complete by reference
Parent reports SHALL retain artifact paths, hashes, exit state, finding ids,
and a bounded failure excerpt of at most 200 lines or 64 KiB while the complete
raw streams remain available through their immutable references.

#### Scenario: Owner fails with a long trace
- **WHEN** a failing owner emits a trace larger than the excerpt limit
- **THEN** the parent report stores a bounded excerpt and the complete stream reference
- **AND** the excerpt limit does not change the failure status
