## ADDED Requirements

### Requirement: Canonical fake AI executes the current public packet path
The canonical fake AI SHALL accept only a successful current open-packet result,
derive its payload from the returned checklist, and submit through the public
current-runtime result surface.

#### Scenario: Fake AI has not ACKed or opened the packet
- **WHEN** fake execution is requested without current ACK/open identity and
  checklist evidence
- **THEN** response generation MUST fail closed
- **AND** it MUST NOT read the raw ledger packet, packet-body contract mirror,
  or private runtime shape helper

#### Scenario: Packet family has no explicit responder
- **WHEN** the current family is not registered by the canonical responder
- **THEN** rehearsal MUST fail as an unimplemented family
- **AND** it MUST NOT return a generic pass/decision payload

#### Scenario: Old checklist is replayed after reissue
- **WHEN** a packet is reissued or its run, route, source generation, packet,
  lease, or contract fingerprint changes
- **THEN** the old checklist MUST be rejected
- **AND** fake AI MUST ACK and open the current packet before retry

### Requirement: Chaos replay includes unbounded-syntax risk classes
Synthetic chaos replay SHALL supplement the finite contract universe with
deterministic parser, size, encoding, replay, concurrency, and cross-run attack
profiles without calling those profiles exhaustive natural-language coverage.

#### Scenario: Malformed or hostile JSON is supplied
- **WHEN** the body contains duplicate keys, invalid numeric values, invalid
  encoding/BOM, excessive size/depth, top-level non-object, or prose wrappers
- **THEN** the public entrypoint MUST return its declared parser/mechanical
  outcome
- **AND** the oracle MUST verify result creation, reissue, and state mutation
  behavior explicitly

### Requirement: Chaos owners cannot survive their execution boundary
Synthetic replay and background chaos owners SHALL preserve one explicit
launcher/descendant process identity and SHALL not accept or reuse evidence
from an interrupted owner until every descendant is terminal.

#### Scenario: Chaos supervisor is cancelled with live descendants
- **WHEN** cancellation, timeout, or interruption leaves one or more child or
  grandchild processes alive or unaccounted
- **THEN** replay MUST report `cleanup-unconfirmed` and a non-passing receipt
- **AND** no unattended retry, daemon replay, or second owner may continue the
  same mutable evidence boundary

#### Scenario: Chaos process tree reaches zero descendants
- **WHEN** the explicit owner records terminal outcomes and proves the
  descendant count is zero
- **THEN** a later fresh owner MAY start under a new execution identity
- **AND** the abandoned partial evidence MUST remain non-authoritative
