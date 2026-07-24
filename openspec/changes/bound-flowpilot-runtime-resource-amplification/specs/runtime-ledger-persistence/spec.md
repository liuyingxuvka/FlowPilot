## ADDED Requirements

### Requirement: Canonically equal state is not rewritten
Every authoritative JSON or text persistence owner SHALL compare the proposed
canonical content with the current durable content before executing atomic
replace.  Canonically equal content SHALL return a no-write result; changed
content SHALL retain the existing lock, flush, fsync, replace, and read-back
verification.

#### Scenario: Equal full run state
- **WHEN** the persistence owner receives a proposed run state canonically equal to the durable state
- **THEN** it reports `written=false`
- **AND** it does not create a temporary file, replace the target, fsync the target, or change its modification time

#### Scenario: Changed full run state
- **WHEN** at least one semantic field differs from the durable state
- **THEN** the persistence owner performs the existing atomic verified write
- **AND** it reports `written=true` only after read-back succeeds

### Requirement: Derived projections are affected-only
Core runtime persistence SHALL rematerialize only projection families affected
by the current in-memory ledger delta, and every projection writer SHALL skip
canonically equal output without creating a persistent dirty-state authority.

#### Scenario: Lease-only change
- **WHEN** a ledger update changes only lease progress
- **THEN** only lease-dependent projections are eligible for a write
- **AND** unrelated packet, result, route, review, closure, and evidence projections remain byte-identical
