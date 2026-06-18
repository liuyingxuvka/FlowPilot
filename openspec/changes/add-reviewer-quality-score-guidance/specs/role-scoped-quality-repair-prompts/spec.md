## ADDED Requirements

### Requirement: PM understands Reviewer quality scores as decision input
FlowPilot SHALL instruct PM to interpret Reviewer quality scores using the same
strict rubric that Reviewer uses, while preserving PM ownership of optimization
and route decisions.

#### Scenario: PM reads scored Reviewer report
- **WHEN** PM receives or opens a Reviewer report containing a quality score
- **THEN** PM prompt guidance MUST explain that `6/10` means the minimum user
  standard is just met, `9/10` is the target, and `10/10` substantially exceeds
  the user's standard
- **AND** PM MUST treat a hard-gate blocker as requiring repair, waiver, route
  mutation, stop, or the existing threshold path before gate pass.

#### Scenario: PM may optimize without a blocker
- **WHEN** Reviewer returns no blocker
- **AND** Reviewer score, findings, or suggestions show useful quality
  improvement below the `9/10` target
- **THEN** PM MUST retain the normal choice to optimize, continue, defer,
  reject, waive with authority, stop, or ask the user
- **AND** Reviewer score MUST NOT become an automatic route or repair command.

### Requirement: Worker repair packets carry Reviewer score context
FlowPilot SHALL instruct workers to read authorized Reviewer score context when
repair or optimization packets include prior Reviewer reports.

#### Scenario: Worker repairs from scored Reviewer blocker
- **WHEN** a repair packet includes authorized prior Reviewer reports or
  blocker context with a quality score
- **THEN** Worker prompt guidance MUST tell the worker to read the score,
  quantitative gap, and requested repair from the authorized materials
- **AND** Worker MUST aim for the `9/10` target inside the packet boundary.

#### Scenario: Worker does not expand scope for score alone
- **WHEN** Reviewer score suggests quality improvement but the improvement
  requires broader scope, changed acceptance, new dependencies, route mutation,
  or another role's authority
- **THEN** Worker MUST report the issue as blocked, `needs_pm`, or PM
  suggestion instead of silently expanding the packet.
