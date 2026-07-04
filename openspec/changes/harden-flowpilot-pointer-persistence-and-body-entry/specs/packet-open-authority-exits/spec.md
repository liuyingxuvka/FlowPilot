## ADDED Requirements

### Requirement: submit-result body entry requires a top-level JSON object
FlowPilot SHALL validate `submit-result` body input at the CLI boundary before
loading the current run ledger or mutating packet result state.

#### Scenario: Inline object body is accepted
- **WHEN** `flowpilot_new.py submit-result` receives `--body` containing valid
  JSON whose top level is an object
- **THEN** FlowPilot MAY pass the exact body text to the existing packet result
  runtime.

#### Scenario: Inline JSON string is rejected
- **WHEN** `flowpilot_new.py submit-result` receives `--body` containing valid
  JSON whose top level is a string
- **THEN** FlowPilot MUST reject the payload as `json_not_object`
- **AND** it MUST NOT unwrap, normalize, or resubmit the string contents as an
  object.

#### Scenario: Body file object is accepted
- **WHEN** `flowpilot_new.py submit-result` receives `--body-file` naming a
  readable file containing a top-level JSON object
- **THEN** FlowPilot MAY submit that file content through the existing packet
  result runtime.

#### Scenario: Body input is malformed or non-object
- **WHEN** body input is empty, malformed JSON, an array, a number, a boolean,
  null, or an unreadable file
- **THEN** FlowPilot MUST reject the command before packet mutation
- **AND** the error MUST name the observed payload kind, the expected top-level
  JSON object, and a safe hint to use `--body-file`.

#### Scenario: Both body modes are provided
- **WHEN** `--body` and `--body-file` are both provided
- **THEN** FlowPilot MUST reject the command before packet mutation.
