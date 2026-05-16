## ADDED Requirements

### Requirement: Controller translates internal progress into plain user language

The Controller SHALL default to explaining user-facing status in plain language:
what is happening now, what FlowPilot is waiting for, and whether the user needs
to act. Controller SHALL avoid leading with internal Router, action, ledger,
packet, ACK, scheduler, receipt, hash, contract, or diagnostic terms unless the
user asks for technical details or those terms are needed to explain a concrete
blocker.

#### Scenario: Controller mentions current progress to the user

- **WHEN** Controller reports current FlowPilot progress or waiting state to the
  user
- **THEN** the message first explains the situation in user-understandable
  language instead of copying internal action names, event names, ledger names,
  packet ids, ACK labels, scheduler labels, hashes, contract names, or
  diagnostic paths.

#### Scenario: User asks for technical details

- **WHEN** the user explicitly asks for technical details or a blocker cannot be
  explained accurately without a technical name
- **THEN** Controller may include the technical name while preserving sealed
  body and role-authority boundaries.

### Requirement: Controller work board carries plain-language reminder

The generated `controller_table_prompt` SHALL include a compact reminder that
Controller should translate internal action, ledger, receipt, packet, wait,
daemon, ACK, and scheduler terms into plain language before mentioning
Controller work to the user.

#### Scenario: Controller reads the generated action ledger

- **WHEN** Router rebuilds `runtime/controller_action_ledger.json`
- **THEN** `controller_table_prompt.text` includes the plain-language reminder
  before or alongside the table-processing instructions.

### Requirement: No new user-reporting mechanism is introduced

This change SHALL NOT add a Router-generated plain summary field, fixed user
report template, Route Sign rewrite, Mermaid rewrite, or new display mechanism.

#### Scenario: Existing display behavior remains unchanged

- **WHEN** FlowPilot displays route signs, Mermaid diagnostics, or existing
  status surfaces
- **THEN** this change only affects Controller guidance and does not introduce a
  new required display artifact.
