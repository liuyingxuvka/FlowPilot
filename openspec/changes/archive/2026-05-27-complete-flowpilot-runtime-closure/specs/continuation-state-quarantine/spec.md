## ADDED Requirements

### Requirement: Prior-run state is quarantined before authority use

FlowPilot SHALL quarantine imported prior-run state before any imported control
state, role identity, route evidence, or generated resource can influence the
current run.

#### Scenario: Continuing from a prior run
- **WHEN** a new current run imports evidence from a prior run
- **THEN** it records the imported source, hash or version, authority status,
  and quarantine disposition under the current run
- **AND** the imported item is read-only evidence until a current-run PM or
  reviewer gate explicitly accepts it for a named purpose.

#### Scenario: Old control state cannot become current
- **WHEN** imported prior state contains old route, frontier, controller,
  daemon, or runtime status files
- **THEN** FlowPilot prevents those files from becoming current-run authority
  unless transformed into current-run records by an explicit import path.

### Requirement: Old role agent identities are audit-only by default

FlowPilot SHALL treat prior-run or prior-task role `agent_id` values as audit
history unless the current run records a same-task continuation match.

#### Scenario: Old agent id appears in imported crew memory
- **WHEN** a prior role `agent_id` is found during continuation startup
- **THEN** the quarantine record marks it audit-only or requires fresh current
  role recovery before role approval can proceed.

#### Scenario: Fresh role recovery clears quarantine
- **WHEN** a current-run role is spawned, restored, or explicitly approved by
  the allowed fallback path
- **THEN** the current-run crew ledger records the current role identity and the
  old `agent_id` remains non-authoritative history.

### Requirement: Old assets and generated resources are not current evidence by default

FlowPilot SHALL prevent old screenshots, icons, route signs, generated images,
or visual artifacts from becoming current evidence without current-run
lineage/disposition.

#### Scenario: Prior visual artifact is imported
- **WHEN** a prior generated or visual artifact is referenced by current work
- **THEN** FlowPilot records whether it is superseded, quarantined,
  discarded, read-only evidence, or explicitly revalidated for a named current
  gate.
