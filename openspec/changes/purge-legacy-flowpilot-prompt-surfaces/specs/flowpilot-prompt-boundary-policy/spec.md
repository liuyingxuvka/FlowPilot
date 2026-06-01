## MODIFIED Requirements

### Requirement: Card Boundary Policy Has Shared Authority
FlowPilot SHALL maintain shared prompt-policy assets or mechanically checked policy text for common card boundaries, including ACK semantics, current packet-lifecycle next-step source, current runtime-output return path, live runtime context, sealed-body limits, and role authority.

#### Scenario: Card uses shared ACK semantics
- **WHEN** a system card, event card, work card, role card, or card bundle is delivered
- **THEN** its policy SHALL state that ACK is receipt only and not semantic completion

#### Scenario: Card uses current packet lifecycle as next-step authority
- **WHEN** a role receives a card or formal output request
- **THEN** the card SHALL point the role to the current run, current packet, current lease, assigned packet body, and `flowpilot_new.py` packet lifecycle command path instead of chat history, memory, old Router state, active-holder lease authority, or old runtime-kit output commands as the next-step authority

### Requirement: Formal Outputs Return Through Current Packet Paths
FlowPilot SHALL require formal role outputs to be written to run-scoped current packet artifacts and submitted through the current `flowpilot_new.py submit-result` path, preserving Controller-visible metadata boundaries.

#### Scenario: Formal output avoids chat body leakage
- **WHEN** a role is asked for a report, result, decision, blocker, or formal output
- **THEN** the prompt SHALL direct the role to submit through the current packet result path and SHALL forbid report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat

#### Scenario: Role authority stays scoped
- **WHEN** a Reviewer, FlowGuard operator, Worker, PM, or Controller reads a prompt card
- **THEN** the card SHALL NOT grant authority outside that role's current runtime-authorized packet scope

#### Scenario: Old runtime output paths are forbidden
- **WHEN** a current prompt, card, skill, or template surface includes formal role-output instructions
- **THEN** it SHALL NOT instruct roles to use `flowpilot_runtime.py`, `submit-output-to-router`, `prepare-output`, old Router daemon action state, or active-holder lease submission authority

### Requirement: Prompt Policy Drift Is Testable
FlowPilot SHALL provide focused validation that card-manifest entries and prompt-policy assets stay aligned for common boundary text and reject forbidden old prompt/control paths in current surfaces.

#### Scenario: Missing common boundary fails validation
- **WHEN** a card that requires runtime output or ACK handling lacks the shared boundary policy
- **THEN** prompt/card validation SHALL fail before installed-skill synchronization

#### Scenario: Forbidden legacy prompt surface fails validation
- **WHEN** a current prompt, card, skill, template, or installed-skill surface contains old role-output, old Router daemon, old runtime-kit, or compatibility prompt authority
- **THEN** prompt/card validation SHALL fail before completion is claimed

#### Scenario: Role-specific content remains allowed
- **WHEN** a card includes domain-specific instructions in addition to shared boundary policy
- **THEN** validation SHALL allow that content as long as it does not contradict the shared current packet policy
