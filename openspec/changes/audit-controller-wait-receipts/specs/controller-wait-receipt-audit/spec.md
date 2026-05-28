## ADDED Requirements

### Requirement: Controller audits formal receipts during waits
When Controller is awake during a nonterminal wait, the system SHALL audit
formal receipt metadata before continuing to wait.

#### Scenario: No formal return is present
- **WHEN** Controller is waiting for a role, card, bundle, packet result, or repair return
- **AND** the audit finds no matching formal receipt, envelope, ledger entry, Router event, or next-action notice
- **THEN** the audit reports `no_formal_return_seen`
- **AND** Controller may continue the ordinary wait without treating chat or aside text as completion.

#### Scenario: Formal return is ready
- **WHEN** the audit finds a matching formal return and Router has exposed the expected Controller next action or release evidence
- **THEN** the audit reports `formal_return_ready`
- **AND** Controller resumes ordinary Controller ledger processing instead of remaining in quiet wait.

#### Scenario: Formal return exists but wait was not released
- **WHEN** the audit finds matching formal return evidence
- **AND** the current wait is still active with no corresponding Controller action, release, or next-action notice
- **THEN** the audit reports `formal_return_seen_but_wait_not_released`
- **AND** the result is a control-plane stuck classification rather than role-work completion.

#### Scenario: Result envelope lacks next-action notice
- **WHEN** a packet result envelope exists for the waited packet
- **AND** no packet-specific router-authored `controller_next_action_notice.json` exists
- **THEN** the audit reports `result_envelope_seen_but_no_next_notice`
- **AND** Controller MUST NOT read the result body to decide the next step.

#### Scenario: Aside claims done without formal receipt
- **WHEN** a `controller_aside` claims submission, completion, or readiness
- **AND** the audit finds no matching formal receipt surface
- **THEN** the audit reports `aside_claim_without_formal_return`
- **AND** Controller MUST NOT treat the aside as evidence or release the wait.

#### Scenario: Formal return evidence is malformed
- **WHEN** a matching formal receipt surface exists but lacks required metadata such as event name, role key, packet id, envelope path, or hash fields needed for mechanical routing
- **THEN** the audit reports `formal_return_malformed`
- **AND** Controller treats the condition as control-plane repair input, not as successful work completion.

### Requirement: Controller wait audit preserves sealed-body boundaries
The wait receipt audit SHALL inspect only formal metadata and SHALL NOT inspect
sealed work bodies or judge work quality.

#### Scenario: Packet result body exists
- **WHEN** a packet result body path is present in an envelope or next-action notice
- **THEN** the audit may record that the body path exists as metadata
- **AND** the audit MUST NOT open, summarize, parse, or validate the body content.

#### Scenario: Role output body exists
- **WHEN** a role-output status packet references a role-output body or directory
- **THEN** the audit may use status and ledger metadata
- **AND** Controller MUST NOT read the role-output body or directory to classify the wait.

### Requirement: Wait audit output is machine-readable and user-explainable
The wait receipt audit SHALL emit a compact structured result that Controller
can include in standby/patrol snapshots and translate into plain language only
when reporting is allowed.

#### Scenario: Audit result is included in standby metadata
- **WHEN** Controller standby or patrol observes an active current wait
- **THEN** the returned metadata includes the audit classification, checked surfaces, matched paths, and authority boundary flags.

#### Scenario: Audit result has no current wait
- **WHEN** no current wait exists
- **THEN** the audit reports `not_applicable`
- **AND** standby/patrol behavior remains governed by the Controller action ledger and Router daemon status.
