## ADDED Requirements

### Requirement: ACK projection cannot become a false blocker
FlowPilot SHALL keep ACK receipts, role work completion, and user-visible
blocker language separate after ACK reconciliation.

#### Scenario: ACK-only card is resolved
- **WHEN** a system-card ACK-only wait has been resolved
- **THEN** Router MUST clear ACK-only blocker wording from current status and
  pending-action summaries while preserving any separate role-output wait.

#### Scenario: Role output remains pending after ACK
- **WHEN** ACK is resolved but the role report or result is still required
- **THEN** Router MUST show the role-output wait as the remaining work and MUST
  NOT reintroduce missing-ACK language for that same card.
