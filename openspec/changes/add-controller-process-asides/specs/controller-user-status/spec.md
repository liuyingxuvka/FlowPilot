## ADDED Requirements

### Requirement: Controller status may use process asides operationally

The Controller SHALL be allowed to use Controller-facing process asides to
explain operational status in plain language, but SHALL NOT present aside text
as formal content, evidence, approval, route decision, report reasoning, or
gate judgment.

#### Scenario: Controller reports submitted status from an aside

- **WHEN** a Controller-facing process aside says a role has submitted a
  formal output or is waiting for Router processing
- **THEN** Controller may tell the user that the formal output has been
  submitted or the system is waiting for processing
- **AND** Controller does not summarize the formal output content from the
  aside.

#### Scenario: Controller sees business content in an aside

- **WHEN** a Controller-facing process aside includes apparent business
  content, evidence, conclusion, recommendation, or approval wording
- **THEN** Controller ignores that content for formal decision purposes
- **AND** Controller does not expose it as a formal user-facing conclusion.
