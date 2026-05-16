## ADDED Requirements

### Requirement: Controller Boundary Confirmation Is Owned By Core Load

For a fresh FlowPilot startup, `load_controller_core` SHALL own the Controller
boundary confirmation postcondition. After the core load is reconciled
successfully, Router SHALL have durable Controller boundary confirmation
evidence and SHALL NOT require a separate fresh-start
`confirm_controller_core_boundary` Controller row.

#### Scenario: Fresh core load records boundary evidence
- **WHEN** `load_controller_core` completes during a fresh startup
- **THEN** Router SHALL record canonical Controller boundary confirmation
  evidence
- **AND** Router SHALL set the Controller role-confirmed flags from that
  evidence
- **AND** the confirmation SHALL include the Controller boundary rules and
  forbidden capabilities

#### Scenario: Fresh startup does not queue redundant boundary row
- **WHEN** Controller boundary evidence is present from `load_controller_core`
- **THEN** Router SHALL NOT schedule `confirm_controller_core_boundary` as the
  next fresh startup Controller action
- **AND** startup reconciliation SHALL continue from the evidence-backed state

### Requirement: Boundary Confirmation Evidence Remains Durable And Canonical

FlowPilot SHALL keep `startup/controller_boundary_confirmation.json` and its
Router/runtime receipt evidence as the durable proof of Controller boundary
confirmation. The removal of the separate fresh-start action SHALL NOT remove
the artifact, receipt, hashes, or boundary checks.

#### Scenario: Pre-review checks rely on evidence
- **WHEN** startup pre-review reconciliation checks Controller readiness
- **THEN** the check SHALL use the confirmation artifact, receipt, and Router
  flags
- **AND** it SHALL NOT fail only because no standalone fresh-start boundary row
  was queued

#### Scenario: Boundary rules are preserved
- **WHEN** Router records Controller boundary confirmation during core load
- **THEN** the confirmation SHALL preserve that Controller cannot approve gates,
  mutate route state, read sealed bodies, or perform PM/Worker/Reviewer work

### Requirement: Legacy Boundary Actions Remain Reconcileable

FlowPilot SHALL continue to accept and reconcile valid
`confirm_controller_core_boundary` evidence for existing runs that already
contain that action. Compatibility SHALL NOT cause new fresh-start runs to
reintroduce the redundant row.

#### Scenario: Existing pending boundary action is accepted
- **WHEN** an existing run contains a pending `confirm_controller_core_boundary`
  action
- **AND** Controller submits valid runtime evidence for that action
- **THEN** Router SHALL reconcile the action and update Controller boundary
  flags

#### Scenario: Reconciled legacy action is not reissued
- **WHEN** a legacy boundary action has already been reconciled from valid
  evidence
- **THEN** Router SHALL NOT reissue another boundary action for the same run
