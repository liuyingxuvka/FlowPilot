## ADDED Requirements

### Requirement: Process asides are not automatic user messages
Controller process asides SHALL remain Controller-only operational context by default and SHALL NOT be automatically relayed as user-visible messages.

#### Scenario: Aside reports routine submission state
- **WHEN** a process aside says a role started, is still working, submitted, retrying, or is waiting for Router processing
- **THEN** Controller may use it as operational context
- **AND** Controller MUST NOT automatically relay the aside text to the user.

#### Scenario: Aside accompanies meaningful user-visible change
- **WHEN** formal Router-owned state separately shows a blocker, user-required action, completion, stop, recovery path, or user-relevant waiting-target change
- **THEN** Controller may explain that formal state to the user in plain language
- **AND** the process aside remains non-authoritative and is not treated as the formal source of the message.
