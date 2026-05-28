## ADDED Requirements

### Requirement: Process asides may prompt formal receipt audit only
Controller process asides SHALL remain non-authoritative and MAY only prompt a
check of formal receipt surfaces.

#### Scenario: Aside says work was submitted
- **WHEN** a `controller_aside` says a role submitted, completed, or prepared work
- **THEN** Controller may run or consult the wait receipt audit
- **AND** Controller MUST NOT treat the aside itself as a formal return, evidence, approval, or Router event.

#### Scenario: Aside contradicts formal receipts
- **WHEN** aside text claims completion
- **AND** formal receipt surfaces do not contain matching return evidence
- **THEN** the system reports `aside_claim_without_formal_return`
- **AND** the formal wait remains unsatisfied.
