## ADDED Requirements

### Requirement: Currentness projection misses are known-friction gates
FlowPilot SHALL register currentness and derived-projection model misses as
known-friction regression gates when real or replayed evidence shows FlowGuard
field modeling previously passed without catching the bug family.

#### Scenario: Same-family currentness miss is replayed
- **WHEN** a replay or focused regression constructs a late result after
noncurrent packet disposition
- **THEN** the known-friction gate MUST require model coverage, runtime
behavior evidence, and ordinary test evidence before the miss is closed

#### Scenario: Derived projection drift is replayed
- **WHEN** a replay or focused regression constructs a packet that is
noncurrent by Router currentness but visible in a derived active-packet view
- **THEN** the known-friction gate MUST fail until the derived view uses the
single currentness predicate
