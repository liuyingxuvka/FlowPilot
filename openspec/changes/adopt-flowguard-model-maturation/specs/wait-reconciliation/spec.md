## ADDED Requirements

### Requirement: ACK Settlement Is Separate From Output Completion
FlowPilot wait reconciliation SHALL model ACK wait settlement separately from durable semantic role-output completion.

#### Scenario: ACK settles receipt wait only
- **WHEN** a valid ACK arrives for a role-work packet that still expects a formal output artifact
- **THEN** FlowPilot settles the ACK wait while preserving the pending output obligation

#### Scenario: Output completion requires durable evidence
- **WHEN** a role-output wait is pending
- **THEN** FlowPilot completes the output obligation only after durable output evidence or a valid terminal disposition exists

### Requirement: ACK-Only Closure Is a Known-Bad Hazard
FlowPilot validation SHALL reject a state where ACK evidence alone completes semantic work that required a role output.

#### Scenario: ACK-only card cannot close output work
- **WHEN** the model mutates so an ACK clears both the ACK wait and required output completion
- **THEN** the focused checker reports the unsafe state as a detected hazard
