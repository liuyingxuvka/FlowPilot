## ADDED Requirements

### Requirement: Roles can include Controller process asides

FlowPilot SHALL allow a role to include an optional short Controller-facing
process aside with packet, result, or role-output metadata for the current
work item.

The process aside SHALL be addressed to Controller, SHALL be labeled as
`process_note_only`, and SHALL be marked as not formal evidence and not
progress authority.

#### Scenario: Role submits a process aside with output metadata

- **WHEN** a role submits current packet, result, or role-output metadata with
  a process aside
- **THEN** Controller can read the aside as operational context
- **AND** the aside is labeled as process-only and non-authoritative.

#### Scenario: Role omits a process aside

- **WHEN** a role submits otherwise valid packet, result, or role-output
  metadata without a process aside
- **THEN** Router continues the formal flow without blocking for the missing
  aside.

### Requirement: Process asides are not formal work content

FlowPilot prompts SHALL instruct roles that process asides are only for current
workflow state, submission state, mechanical blockers, waiting, retrying, or
recovery.

Process asides SHALL NOT be used for formal work content, evidence, report
reasons, conclusions, recommendations, approvals, route decisions, or gate
judgment.

#### Scenario: Work packet reminds role about aside boundaries

- **WHEN** Router or runtime presents a current work packet, result submission
  prompt, or role-output submission prompt to a role
- **THEN** the prompt explains that the optional process aside is for short
  process status only
- **AND** the prompt says formal content remains in the formal body, report,
  result, or decision file.

#### Scenario: Formal content appears in an aside

- **WHEN** Controller sees an aside that appears to include formal work content
- **THEN** Controller does not use that content for evidence, approval, route
  movement, or user-facing formal conclusions
- **AND** Controller directs the role to keep formal content in the formal
  output path when follow-up is needed.

### Requirement: Router preserves asides without semantic authority

Router SHALL preserve and expose process aside metadata to Controller when
present, but Router SHALL NOT semantically inspect aside text, derive events
from aside text, satisfy waits from aside text, advance gates from aside text,
or use aside text as evidence.

#### Scenario: Aside accompanies an incomplete formal output

- **WHEN** a process aside exists but the required formal output, ACK, or event
  is missing
- **THEN** Router keeps waiting for the required formal artifact or event
- **AND** the aside does not satisfy the wait.

#### Scenario: Aside accompanies a valid formal output

- **WHEN** a valid formal output is submitted with a process aside
- **THEN** Router evaluates the formal output through the existing formal
  runtime path
- **AND** the aside does not affect the formal validation result.

### Requirement: Worker asides remain Controller-only

Worker process asides SHALL be visible to Controller only and SHALL NOT create
Worker-to-Worker communication.

#### Scenario: Worker A writes an aside

- **WHEN** Worker A includes a process aside with current work metadata
- **THEN** Controller can read or relay process status as allowed
- **AND** Worker B does not receive Worker A's aside as a work instruction,
  evidence source, or informal conversation.
