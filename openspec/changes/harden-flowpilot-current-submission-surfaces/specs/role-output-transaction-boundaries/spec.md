## ADDED Requirements

### Requirement: Behavior-bearing old aliases are rejected
FlowPilot SHALL reject current packet result payloads that rely on old alias
fields for behavior-bearing decisions or request routing.

#### Scenario: PM disposition reason alias is not accepted
- **WHEN** PM submits a package disposition or formal gate payload that omits
  `decision_reason` and provides only `reason`
- **THEN** Router MUST reject the payload instead of treating `reason` as a
  valid current decision reason.

#### Scenario: Material sufficiency old aliases are not accepted
- **WHEN** a material-sufficiency payload omits `reviewed_by_role` or
  `runtime_open_receipt_refs` and provides only old aliases such as
  `checked_by_role` or `runtime_open_receipts`
- **THEN** Router MUST reject the payload instead of normalizing those aliases.

#### Scenario: PM request old aliases are not accepted
- **WHEN** a PM request payload omits current request fields and provides only
  old aliases such as `mode`, `from_role`, `recipient_role`, or `kind`
- **THEN** Router MUST reject the payload instead of constructing a current
  request from aliases.

