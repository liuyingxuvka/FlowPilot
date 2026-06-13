## ADDED Requirements

### Requirement: Reviewer challenges implementation intent alignment

FlowPilot SHALL require a human-like Reviewer implementation-intent challenge that checks user-value preservation, PM intent specificity, FlowGuard model fidelity, and low-quality completion resistance before route drafting.

#### Scenario: Reviewer passes implementation intent

- **WHEN** Reviewer passes the implementation-intent challenge
- **THEN** the report identifies the PM intent, the FlowGuard target-realization model, alignment evidence, hard-part coverage, and any accepted residual risk

#### Scenario: Reviewer omits alignment check

- **WHEN** Reviewer approval does not check PM intent against the FlowGuard target-realization model
- **THEN** the review does not unlock route skeleton drafting
