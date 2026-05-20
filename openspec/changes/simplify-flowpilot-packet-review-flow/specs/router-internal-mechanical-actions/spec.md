## ADDED Requirements

### Requirement: Router mechanical proof has a narrow replacement scope
Router-owned proof SHALL replace Reviewer rechecking only for mechanical envelope, ledger, role-target, hash, and Controller body-boundary facts. Reviewer SHALL remain responsible for semantic package review, source sufficiency, result quality, acceptance risk, and independent challenge.

#### Scenario: Reviewer trusts Router-computable checks
- **WHEN** Router has recorded proof for packet target role, envelope hash, result hash, relay ledger state, and Controller sealed-body exclusion
- **THEN** Reviewer cards MAY cite that proof instead of manually rechecking those mechanical facts
- **AND** Reviewer cards MUST still require direct review of the formal package content and task-specific quality risks.

#### Scenario: Router proof cannot approve semantic work
- **WHEN** Router mechanical proof is complete but PM formal package content has not been reviewed
- **THEN** Reviewer SHALL NOT pass the quality, material, research, or node-completion gate from Router proof alone.
