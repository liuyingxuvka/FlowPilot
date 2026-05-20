## ADDED Requirements

### Requirement: Card Boundary Policy Has Shared Authority
FlowPilot SHALL maintain shared prompt-policy assets or mechanically checked policy text for common card boundaries, including ACK semantics, Router-authorized next-step source, runtime-output return path, live runtime context, sealed-body limits, and role authority.

#### Scenario: Card uses shared ACK semantics
- **WHEN** a system card, event card, work card, role card, or card bundle is delivered
- **THEN** its policy SHALL state that ACK is receipt only and not semantic completion

#### Scenario: Card uses Router as next-step authority
- **WHEN** a role receives a card or formal output request
- **THEN** the card SHALL point the role to Router-provided runtime context, allowed external events, active-holder lease, or output contract instead of chat history or memory as the next-step authority

### Requirement: Formal Outputs Return Through Runtime Paths
FlowPilot SHALL require formal role outputs to be written to run-scoped artifacts and submitted through the Router-directed runtime path, preserving Controller-visible metadata boundaries.

#### Scenario: Formal output avoids chat body leakage
- **WHEN** a role is asked for a report, result, decision, blocker, or formal output
- **THEN** the prompt SHALL direct the role to submit through the runtime path and SHALL forbid report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat

#### Scenario: Role authority stays scoped
- **WHEN** a Reviewer, Officer, Worker, PM, or Controller reads a prompt card
- **THEN** the card SHALL NOT grant authority outside that role's existing Router-authorized scope

### Requirement: Prompt Policy Drift Is Testable
FlowPilot SHALL provide focused validation that card-manifest entries and prompt-policy assets stay aligned for common boundary text.

#### Scenario: Missing common boundary fails validation
- **WHEN** a card that requires runtime output or ACK handling lacks the shared boundary policy
- **THEN** prompt/card validation SHALL fail before installed-skill synchronization

#### Scenario: Role-specific content remains allowed
- **WHEN** a card includes domain-specific instructions in addition to shared boundary policy
- **THEN** validation SHALL allow that content as long as it does not contradict the shared policy
