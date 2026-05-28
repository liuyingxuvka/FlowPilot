## ADDED Requirements

### Requirement: User status explains audited wait state plainly
When Controller is allowed to report wait status to the user, it SHALL use the
wait receipt audit classification to distinguish ordinary waiting from
control-plane stuck states without exposing sealed content.

#### Scenario: Ordinary wait status
- **WHEN** the user asks for status during a wait
- **AND** the wait receipt audit reports `no_formal_return_seen`
- **THEN** Controller explains that no formal return record has arrived yet.

#### Scenario: Formal return is ready
- **WHEN** the wait receipt audit reports `formal_return_ready`
- **THEN** Controller explains that a formal return has arrived and it is moving through the normal handoff path.

#### Scenario: Control plane appears stuck
- **WHEN** the wait receipt audit reports `formal_return_seen_but_wait_not_released` or `result_envelope_seen_but_no_next_notice`
- **THEN** Controller explains that the formal return appears to exist but the control flow has not produced the expected next step.

#### Scenario: Aside-only completion claim
- **WHEN** the wait receipt audit reports `aside_claim_without_formal_return`
- **THEN** Controller explains that only a status note was found and no formal submission record is available.

#### Scenario: Sealed content remains hidden
- **WHEN** Controller reports any audited wait state
- **THEN** the message MUST NOT include sealed work body contents, body summaries, or quality judgments.
