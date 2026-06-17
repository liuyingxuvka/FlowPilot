# flowpilot-prompt-boundary-policy Spec Delta

## ADDED Requirements

### Requirement: FlowGuard repair prompts must require subject-bound semantic coverage

FlowGuard repair recheck prompts SHALL require the operator to consume the authorized subject result and answer the active blocker, not merely validate result shape, field presence, or current contract format.

#### Scenario: FlowGuard operator receives blocker-bound recheck contract

- **GIVEN** a FlowGuard packet includes `semantic_recheck_contract`
- **WHEN** the FlowGuard operator prepares its result
- **THEN** the prompt requires `semantic_recheck.blocker_id`
- **AND** it requires proof that the subject result was consumed
- **AND** it forbids shape-only or current-contract-only pass boundaries

### Requirement: PM repair prompts must request formal blocker-bound rechecks

PM repair prompts SHALL preserve blocker identity and request formal FlowGuard semantic recheck evidence when a Reviewer blocker requires FlowGuard revalidation.

#### Scenario: PM asks for FlowGuard recheck with blocker identity

- **GIVEN** Reviewer blocks a subject result for missing or inadequate FlowGuard evidence
- **WHEN** PM prepares the repair path
- **THEN** PM keeps the blocker id as a formal field
- **AND** requests a blocker-bound FlowGuard recheck rather than prose-only evidence
