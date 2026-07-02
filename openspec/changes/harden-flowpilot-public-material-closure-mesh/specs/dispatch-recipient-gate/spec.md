# dispatch-recipient-gate Specification

## ADDED Requirements

### Requirement: Current role and output ownership stay aligned

Packet envelope responsibility, output contract recipient, handoff contract recipient, current lease holder, and submitted result origin SHALL refer to the same current requested role/responsibility.

#### Scenario: Old agent identity appears in a new packet
- **WHEN** a result or packet references an old agent/role identity that is not the current lease holder for the current packet
- **THEN** runtime or control-surface checks MUST reject or route repair before gate approval.

### Requirement: Accepted result projection cannot regress

Accepted packet/result references SHALL remain bound to current valid packet status and active route context.

#### Scenario: Accepted result id points at a nonterminal or noncurrent packet
- **WHEN** an accepted result id is present but the packet/result status or route context does not permit closure
- **THEN** final projection and gate closure MUST be blocked.
