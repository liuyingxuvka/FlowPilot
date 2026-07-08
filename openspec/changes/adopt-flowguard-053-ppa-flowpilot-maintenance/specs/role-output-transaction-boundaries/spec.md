## ADDED Requirements

### Requirement: Role Output Fields Remain Current-Contract Only
FlowPilot formal role output contracts SHALL require each successful field to
belong to one current result family and SHALL reject unsupported aliases,
fallback prose, generated substitutes, or historical shapes.

#### Scenario: Role output uses unsupported field
- **WHEN** Worker, Reviewer, FlowGuard operator, or PM output contains an unsupported old field, alias, wrapper, fallback, or generated substitute
- **THEN** runtime or validation SHALL reject the output through the current contract path
- **AND** no result id, accepted pointer, or completion evidence SHALL be mutated as accepted success.

### Requirement: Runtime Does Not Generate Role Summaries
If PM-visible role summaries remain canonical, runtime SHALL validate and relay
only role-authored current fields and SHALL NOT generate semantic prose from
sealed packet or result bodies.

#### Scenario: Summary field is missing
- **WHEN** a result contract requires a role-authored summary field and the submitted result omits it
- **THEN** runtime SHALL mechanically reject or reissue through the current packet family
- **AND** it SHALL NOT synthesize a substitute summary from sealed body text.
