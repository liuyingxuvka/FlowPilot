## MODIFIED Requirements

### Requirement: Stateful Controller receipt postconditions are complete and idempotent

Stateful Controller receipt folds SHALL be replayable and SHALL update every authoritative lifecycle record named by the postcondition contract.

#### Scenario: Material scan result relay receipt is replayed
- **WHEN** a `relay_material_scan_results_to_pm` Controller receipt is folded
- **THEN** Router MUST set the material result relay flag
- **AND** Router MUST update the active material scan batch lifecycle to `results_relayed_to_pm`
- **AND** reapplying the same receipt MUST NOT duplicate batch or history side effects

#### Scenario: Registered fold has missing lifecycle evidence
- **WHEN** a receipt fold has a Router flag but cannot validate the matching durable lifecycle record
- **THEN** Router MUST leave the postcondition unresolved or emit a bounded control blocker
- **AND** Router MUST NOT mark the postcondition fully reconciled from the flag alone
