## ADDED Requirements

### Requirement: Current handoff contract is the only mechanical result authority
FlowPilot SHALL derive the role-visible submission checklist only from the
current packet envelope's complete `current_handoff_contract` and SHALL reject
missing, malformed, stale, or conflicting authority instead of reading packet-
body contract mirrors or private runtime helpers.

#### Scenario: Packet body conflicts with envelope
- **WHEN** a sealed packet body contains required fields, branch shapes, or a
  minimal shape different from the envelope handoff contract
- **THEN** open-packet MUST project the envelope contract unchanged
- **AND** the body conflict MUST NOT create an alternate valid submission path

#### Scenario: Envelope contract is incomplete
- **WHEN** the handoff omits a required mechanical surface such as forbidden
  fields, aliases, branches, options, types, or current identity
- **THEN** open-packet MUST fail closed with repairable current-contract
  feedback
- **AND** it MUST NOT fill the gap from packet body or remembered family data

#### Scenario: A retired shape can be translated to the current shape
- **WHEN** a packet, result, role, route, review, resume, or evidence input uses
  a retired field, alias, wrapper, prose shape, or alternate authority path
- **THEN** the current owner MUST reject the input with structured repair
  feedback
- **AND** it MUST NOT translate, default, normalize, or route the input through
  a compatibility or fallback success path

### Requirement: Current authority references are structured and exact
FlowPilot SHALL carry original user intent, accepted requirements, active
route/node/packet identity, and current evidence through structured reference
items in the existing handoff and `node_context_package.relevant_references`
surfaces, without creating a second authority ledger.

Each reference item MUST identify its `reference_kind`, authority id, owner,
run- or repository-scoped path, content fingerprint, consumer scope, and every
identity required by that kind, including applicable run id, route version,
node id, packet id, result id, and source generation.

#### Scenario: Current role receives authoritative project context
- **WHEN** Runtime dispatches a substantive current role
- **THEN** the role-visible handoff MUST include structured references to the
  applicable current user/contract/runtime/evidence authorities
- **AND** each reference MUST be verifiable without reading chat history,
  selecting the newest artifact, or guessing a missing identity

#### Scenario: Authority reference is stale or conflicting
- **WHEN** a reference is missing, duplicated, foreign-run, hash-mismatched,
  superseded, or inconsistent with another current authority
- **THEN** the current owner MUST block with the exact invalid reference and
  repair command
- **AND** it MUST NOT promote an older path, prose label, role memory, or
  alternate reference to current authority

### Requirement: Current execution sources reject historical authority
FlowPilot SHALL accept current formal progress only from current supported
runtime/role/manual-resume sources; daemon replay and old role aliases SHALL be
negative or historical-only inputs.

#### Scenario: Daemon replay submits an otherwise legal current result
- **WHEN** execution source is `daemon_replay`
- **THEN** the current stage MUST reject or block the submission
- **AND** it MUST NOT continue current-stage progress

#### Scenario: Unsupported responsibility is supplied
- **WHEN** a packet or route uses an unknown or retired responsibility alias
- **THEN** runtime MUST reject it
- **AND** it MUST NOT silently normalize the responsibility to Worker

### Requirement: Foreground start retry preserves one current invocation
FlowPilot SHALL allocate and persist one fresh bootstrap for one public
`start` command before startup advancement. Writer-contention retries SHALL
resume that bootstrap, reattach the exact current-run in-flight daemon, and
preserve successfully completed folded-action evidence.

#### Scenario: Writer contention occurs after startup advancement begins
- **WHEN** one or more startup actions completed before a current runtime
  writer blocks the next action
- **THEN** settlement MUST wait within the current bounded budget and resume
  the same bootstrap without another fresh-run allocation
- **AND** the final command receipt MUST include the actions completed before
  and after contention

#### Scenario: Startup authority is ambiguous
- **WHEN** one command observes more than one allocated run or more than one
  exact live startup-daemon identity for the current run
- **THEN** startup MUST fail closed with the conflicting current identities
- **AND** it MUST NOT choose a newest run, start another daemon, or continue
  through an alternate startup path

### Requirement: Manual resume targets exactly the current requested roles
FlowPilot SHALL make public `flowpilot_new.py resume` plus its returned
`foreground_duty` the only formal resume authority and SHALL derive one exact,
deduplicated role target set from current unresolved packet or Controller-wait
obligations plus the immediate foreground-duty recipient when role work is
required.

#### Scenario: Current unresolved obligations require role recovery
- **WHEN** manual resume finds current unresolved role-owned obligations
- **THEN** resume MUST include every and only the roles that own those
  obligations plus any immediate role recipient required by foreground duty
- **AND** each target MUST carry current-run binding or replacement evidence

#### Scenario: Same-run role slot is idle
- **WHEN** a role binding or memory slot exists in the current run but owns no
  unresolved obligation and is not the immediate foreground-duty recipient
- **THEN** resume MUST leave the slot as continuity or audit context
- **AND** it MUST NOT open, restore, replace, wait on, or count that role as a
  required resume target

#### Scenario: Historical or fixed role set is available
- **WHEN** prior-run bindings, chat history, route history, a fixed role
  topology, or all same-run role slots suggest additional roles
- **THEN** those roles MUST be excluded unless current obligation evidence
  independently requires them
- **AND** the retained diagnostic router MUST NOT use the wider set as current
  progress, resume-success, or completion evidence

#### Scenario: Resume target set is not exact
- **WHEN** a required role is missing, an idle role is added, a role is
  duplicated, or a binding is stale or foreign-run
- **THEN** resume MUST block with the current target-set discrepancy and named
  recovery path
- **AND** PM MUST be included only when a current PM decision is actually
  required
