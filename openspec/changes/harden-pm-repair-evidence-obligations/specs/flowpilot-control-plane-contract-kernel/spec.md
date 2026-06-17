## ADDED Requirements

### Requirement: Repair evidence obligations stay current through packet/result contracts
FlowPilot SHALL carry blocker-derived repair evidence obligations through the
existing PM repair packet/result contract and SHALL reject stale, unknown,
duplicate, or unsupported obligation references.

#### Scenario: Blocker missing evidence becomes PM packet obligations
- **WHEN** runtime materializes a semantic, review, FlowGuard, or validation
  blocker that names missing required evidence, stale evidence, missing
  matching FlowGuard report, direct evidence, final replay, ordinary validation,
  route/node context, or waiver authority
- **THEN** the PM repair packet body MUST include
  `repair_evidence_obligations` rows derived from the current blocker
- **AND** each row MUST include a stable obligation id, source blocker id,
  evidence kind, required action, allowed resolution, and downstream consumer.

#### Scenario: Unknown obligation id is rejected
- **WHEN** PM submits `repair_obligation_disposition` containing an obligation
  id that is not present in the current PM repair packet
- **THEN** runtime MUST mechanically reject the result
- **AND** the rejection MUST name the unsupported obligation field path.

#### Scenario: Registry-only repair cannot satisfy evidence
- **WHEN** PM claims an obligation is already satisfied only by an acceptance
  registry, summary, reason, or prior historical result
- **THEN** runtime MUST reject the result unless the disposition cites a current
  authorized evidence reference or an explicit authority waiver allowed by the
  blocker.

#### Scenario: Downstream recheck consumes obligation context
- **WHEN** runtime opens a repair packet, FlowGuard semantic recheck, or
  Reviewer recheck after a PM repair decision
- **THEN** the current repair obligation ids and required evidence kinds MUST be
  visible to the downstream consumer
- **AND** blocker clearance MUST require the downstream check to consume the
  current obligation context.

### Requirement: Required sealed bodies have current downstream readers
FlowPilot SHALL expose required sealed result/report bodies through the current
packet handoff contract and SHALL reject a packet result when required
authorized bodies were not opened by the assigned role.

#### Scenario: Related blocker bodies are projected into handoff contract
- **WHEN** runtime creates a PM repair, repair-worker, FlowGuard recheck, or
  Reviewer recheck packet from a blocker
- **THEN** `current_handoff_contract.input_material_manifest` MUST include the
  packet's `authorized_result_reads`, required read ids, required read count,
  and an assertion that all required authorized bodies must be opened before
  submit
- **AND** the packet body and envelope MUST point to the same authorized read
  rows.

#### Scenario: Downstream role opens all required bodies
- **WHEN** the assigned role uses `flowpilot_new.py open-packet`
- **THEN** runtime MUST deliver every authorized input material for that role
  and record a current open receipt keyed by packet, lease, role, result id,
  and body hash
- **AND** submit-result MUST pass the body-read gate only when every required
  read has a matching receipt.

#### Scenario: Partial body read is rejected
- **WHEN** a packet declares more than one required authorized result body
- **AND** the assigned role opens only the packet body or only one authorized
  result body
- **THEN** submit-result MUST report the missing required result body ids
- **AND** the packet MUST stay unaccepted until the assigned role opens the
  remaining current bodies or PM chooses a legal stop/repair path.
