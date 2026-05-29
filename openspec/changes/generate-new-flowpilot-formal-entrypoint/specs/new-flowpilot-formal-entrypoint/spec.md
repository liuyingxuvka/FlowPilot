## ADDED Requirements

### Requirement: New Formal Entrypoint

Fresh formal FlowPilot invocations SHALL enter the new black-box runtime
through `flowpilot_new.py start`.

#### Scenario: User starts FlowPilot

- **WHEN** the user explicitly asks to use FlowPilot
- **THEN** the assistant MUST run the new formal entrypoint
- **AND** the old `flowpilot_router.py start` path MUST NOT be used as fresh-run
  authority.

### Requirement: Reused Startup UI Only

The new FlowPilot SHALL reuse the existing native startup intake UI as the
only required UI surface.

#### Scenario: Startup completes

- **WHEN** the native startup UI returns a confirmed result
- **THEN** the new runtime MUST record a sealed startup-intake body and public
  envelope in the current run ledger
- **AND** the startup body MUST NOT appear in chat or public status.

#### Scenario: Headless startup artifact exists

- **WHEN** a startup artifact was produced through headless or scripted mode
- **THEN** it MAY be used for rehearsal tests
- **AND** it MUST NOT prove formal interactive startup.

### Requirement: New Ledger Authority

After startup intake, the new FlowPilot SHALL use `.flowpilot/runs/<run-id>/ledger.json`
as the authority for route, packet, lease, FlowGuard, review, validation, and
closure state.

#### Scenario: Old state exists

- **WHEN** old route state, old agent ids, old display projection, or old result
  artifacts exist
- **THEN** they MUST remain reference or diagnostic material only
- **AND** they MUST NOT advance a new run.

### Requirement: Dynamic Agent Responsibilities

The new FlowPilot SHALL request agent leases by current responsibility instead
of requiring a fixed six-agent startup crew.

#### Scenario: First PM packet is issued

- **WHEN** the new route has a PM-bound startup packet
- **THEN** the next action MUST request a PM lease
- **AND** no fixed six-agent startup requirement is allowed.

### Requirement: New Entrypoint End-To-End Closure

The new FlowPilot SHALL be able to progress from startup intake to final
backward closure through current-run packet, FlowGuard, review, and validation
evidence.

#### Scenario: Rehearsal end-to-end run

- **WHEN** a deterministic fake-host rehearsal supplies a valid result,
  targeted FlowGuard evidence, independent review, and validation evidence
- **THEN** final closure MUST complete
- **AND** the public status MUST still hide sealed bodies.
