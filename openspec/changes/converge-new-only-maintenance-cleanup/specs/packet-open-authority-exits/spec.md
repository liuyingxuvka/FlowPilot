## ADDED Requirements

### Requirement: Reviewer-Named Relay Compatibility Is Not Current Authority
FlowPilot SHALL use recipient-neutral or current recipient-bound relay checks for
packet/result authority and SHALL NOT treat old reviewer-named helper paths as a
current authorization surface for PM-bound results.

#### Scenario: PM-bound result is opened
- **WHEN** a result is bound to the project manager for package disposition
- **THEN** body access authority comes from the current packet runtime relay, ledger,
  hash, and recipient checks
- **AND** an old reviewer-named relay path SHALL NOT imply Reviewer approval,
  Reviewer raw body access, or PM disposition completion.
