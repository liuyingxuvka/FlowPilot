# flowpilot-artifact-authority Specification

## Purpose
TBD - created by archiving change unify-flowpilot-control-plane-contracts. Update Purpose after archive.
## Requirements
### Requirement: Signed packet and result envelopes are immutable originals

FlowPilot SHALL NOT rewrite a packet or result envelope after a Controller relay signature binds the envelope hash.

#### Scenario: Unsupported historical migration finds missing material packet projection fields
- **WHEN** a material packet envelope contains a Controller relay signature
- **AND** unsupported historical migration needs to backfill result body, result envelope, write target, or output contract projection fields
- **THEN** migration MUST preserve the envelope file bytes and signed hash
- **AND** migration MAY update mutable indexes, packet ledger projection fields, or a migration sidecar
- **AND** the migration sidecar MUST identify the packet and the projection fields it supplied

#### Scenario: Unsupported historical migration sees an unsigned envelope
- **WHEN** a material packet envelope has no Controller relay signature
- **THEN** migration MAY update compatible envelope projection fields
- **AND** it MUST still avoid reading or rewriting sealed packet bodies

### Requirement: PM formal gate release has reviewer-readable artifact evidence

FlowPilot SHALL require an absorbed PM package disposition to create or reference a reviewer-readable formal gate package.

#### Scenario: PM absorbs worker package results
- **WHEN** PM records an absorbed disposition for material scan, research, or current-node worker results
- **THEN** the disposition MUST include `formal_gate_package_path` and `formal_gate_package_hash`
- **AND** the referenced artifact MUST identify packet IDs, result envelope paths, reviewer scope, and content boundary
- **AND** Reviewer MUST NOT be expected to read raw worker result bodies

### Requirement: Self-check templates and parser share accepted pass vocabulary

FlowPilot SHALL parse the same pass/fail vocabulary that role output templates permit in the Contract Self-Check section.

#### Scenario: Worker writes status pass
- **WHEN** a result body contains a Contract Self-Check section with `status: pass`
- **THEN** the parser MUST mark the self-check as completed and passed
- **AND** the source output contract check MUST still be enforced when a source contract ID is declared
