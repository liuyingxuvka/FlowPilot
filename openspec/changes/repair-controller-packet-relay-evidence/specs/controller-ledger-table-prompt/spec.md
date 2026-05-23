## ADDED Requirements

### Requirement: Controller relay rows name runtime relay before receipt
The Controller ledger prompt SHALL tell Controller that every packet/result relay row must run the Router-provided runtime relay operation before writing a `done` receipt.

#### Scenario: Relay row prompt forbids path-only completion
- **WHEN** Controller reads a packet/result relay row
- **THEN** the prompt MUST state that sending envelope paths in chat, ticking a checklist, or writing a self-attested receipt is not relay completion
- **AND** the prompt MUST define valid relay completion as runtime relay evidence in the envelope and packet ledger

#### Scenario: Relay row prompt preserves sealed-body boundary
- **WHEN** Controller executes a packet/result relay row
- **THEN** the prompt MUST state that Controller relays envelopes only and MUST NOT open, summarize, repair, or execute sealed bodies
