## ADDED Requirements

### Requirement: PM package disposition is formal packet-release evidence
FlowPilot SHALL require registry-backed PM package disposition evidence before material, research, or current-node packet results can be released to reviewer gates.

#### Scenario: Reviewer release waits for formal PM disposition
- **WHEN** worker packet results have returned to PM
- **THEN** Router MUST NOT release a reviewer formal gate package until PM records a registry-backed package result disposition

#### Scenario: Packet evidence cannot bypass PM disposition contract
- **WHEN** packet ledger evidence exists but the PM disposition is missing, manually shaped, or not bound to the expected contract
- **THEN** Router MUST keep reviewer release blocked and report the missing formal PM disposition boundary
