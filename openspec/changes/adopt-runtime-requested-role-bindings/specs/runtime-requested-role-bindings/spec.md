## ADDED Requirements

### Requirement: Runtime binds only requested roles
FlowPilot SHALL create, attach, restore, or replace a role binding only when the
current runtime action requires that responsibility.

#### Scenario: Lease action binds requested role
- **WHEN** the current runtime action is `lease_agent` for a responsibility
- **THEN** Controller uses a host-supported role mechanism for that
  responsibility only
- **AND** Controller records the addressable role id returned by the host

#### Scenario: Unrequested role is not opened
- **WHEN** no current runtime action requires a responsibility
- **THEN** Controller MUST NOT open, restore, or replace that role solely from
  historical startup topology, chat memory, or old role records

### Requirement: Role mechanism remains host abstract
FlowPilot SHALL treat the host implementation of a role binding as an
implementation detail while preserving runtime evidence boundaries.

#### Scenario: Host provides an addressable role context
- **WHEN** a host-supported role mechanism returns an addressable id for the
  requested role
- **THEN** FlowPilot records that id as the role binding evidence
- **AND** FlowPilot does not require the prompt to name any host-specific
  mechanism

#### Scenario: Host cannot provide a requested role binding
- **WHEN** the requested role cannot be opened, attached, restored, or replaced
  with an addressable id
- **THEN** FlowPilot records a role-binding blocker or follows the
  router-provided recovery path
- **AND** FlowPilot MUST NOT claim that the role is live from intent, chat text,
  old ids, or a timeout alone

### Requirement: Requested role binding preserves evidence boundaries
FlowPilot SHALL require every active role binding to remain tied to current-run
runtime evidence before dependent work can continue.

#### Scenario: ACK is not completion
- **WHEN** a requested role binding acknowledges a packet, card, or work item
- **THEN** FlowPilot treats ACK as liveness and receipt only
- **AND** dependent work still waits for the runtime-visible result, blocker,
  or next action required by the ledger

#### Scenario: Result returns through runtime
- **WHEN** a requested role produces a formal report, result, blocker, or
  decision
- **THEN** the role writes it to the run-scoped output required by the runtime
- **AND** submits it through the runtime path so Controller sees only allowed
  metadata, paths, and hashes

#### Scenario: Stale role id is rejected
- **WHEN** an addressable role id belongs to another run, old route, archived
  memory packet, or unverifiable host context
- **THEN** FlowPilot rejects that id as current role-binding evidence
- **AND** requires recovery, replacement, or an explicit blocker before
  dependent work resumes
