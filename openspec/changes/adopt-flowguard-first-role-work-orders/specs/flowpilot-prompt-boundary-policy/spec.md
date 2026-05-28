## ADDED Requirements

### Requirement: Core cards carry FlowGuard work-order/report boundaries
FlowPilot SHALL update core system, role, PM phase, Officer, Reviewer, Worker,
and event cards that make or inspect non-trivial decisions so they reference
the FlowGuard work-order/report protocol.

#### Scenario: PM phase card requires FlowGuard traceability
- **WHEN** a PM phase card governs product architecture, child-skill
  selection, route drafting, node acceptance, officer requests, repair,
  evidence quality, final ledger, resume, or closure
- **THEN** the card SHALL require FlowGuard work-order/report references or a
  scoped non-required reason for non-trivial judgement
- **AND** the card SHALL preserve PM as the decision owner.

#### Scenario: Officer card executes work order but keeps authority bounded
- **WHEN** an Officer card asks for model, route, validation, repair, or
  mesh-related analysis
- **THEN** the card SHALL instruct the Officer to answer the assigned
  FlowGuard work order, choose the smallest applicable FlowGuard route, and
  return a file-backed report
- **AND** the card SHALL forbid route mutation, gate approval, and completion
  approval by the Officer.

#### Scenario: Reviewer card validates FlowGuard support
- **WHEN** a Reviewer card inspects a FlowGuard-backed artifact or gate
- **THEN** the card SHALL require checks for report existence, freshness,
  scope fit, skipped checks, progress-only evidence, PM acceptance, and role
  authority
- **AND** the card SHALL not require Reviewer to rerun all FlowGuard modeling
  unless PM explicitly routes that work.

### Requirement: Prompt validation detects missing FlowGuard markers
FlowPilot SHALL provide focused validation that core cards include required
FlowGuard work-order/report markers and do not weaken existing authority
boundaries.

#### Scenario: Core card omits FlowGuard marker
- **WHEN** validation scans a core PM, Officer, Reviewer, Worker, Controller,
  or event card in the FlowGuard-first surface
- **THEN** validation SHALL fail if required work-order/report vocabulary is
  missing
- **AND** validation SHALL fail if the card grants FlowGuard decision power to
  Controller, Worker, Officer, or Reviewer beyond their existing role.

#### Scenario: Non-core or legacy card remains compatible
- **WHEN** a card is outside the FlowGuard-first core surface or only preserves
  legacy compatibility behavior
- **THEN** validation MAY skip the marker requirement
- **AND** the card still SHALL NOT contradict Router authority, sealed-body
  boundaries, or role-scoped work authority.
