## ADDED Requirements

### Requirement: Reviewer execution consumes delivered review policy
Reviewer fake-AI and current role execution SHALL use the `review_window` and
`review_depth_rule` delivered by the current open-packet result and SHALL NOT
reconstruct the policy from a static flow-id registry.

#### Scenario: Delivered review policy is missing
- **WHEN** a review packet's open result lacks its declared review-depth rule
- **THEN** Reviewer execution MUST block as an incomplete current handoff
- **AND** it MUST NOT substitute a generic or statically reconstructed policy

#### Scenario: Delivered policy is tampered
- **WHEN** the delivered flow id, lifecycle stage, material requirements, or
  review-depth rule conflicts with the current handoff fingerprint
- **THEN** fake and real review execution MUST reject the packet before pass
  evidence is produced

### Requirement: Substantive roles retain the existing complete-workstream structure
Every substantive PM, Worker, research/evidence Worker, Reviewer, FlowGuard
Operator, and helper result SHALL include the existing `Workstream Plan and
Completion` subsection inside `Contract Self-Check` and account for numbered
steps, intended outcomes, status, evidence, deviations, delegation
integration, verification, unresolved items, and claim consistency.

#### Scenario: Workstream structure is missing or contradictory
- **WHEN** a mechanically valid result omits the workstream subsection, leaves
  required steps unaccounted, fails to integrate delegated work, or claims
  completion while a required step is partial or blocked
- **THEN** Runtime MUST NOT invent, repair, or semantically score the missing
  plan
- **AND** Reviewer MUST inspect the real artifacts and evidence and block when
  completeness or claim consistency is not established

#### Scenario: Workstream structure is present
- **WHEN** a substantive result includes all required workstream rows
- **THEN** their presence MUST NOT by itself prove semantic completeness,
  evidence quality, or satisfaction of the original user intent
- **AND** Reviewer MUST compare the rows with structured current-authority
  references, actual artifacts, delegated outputs, and current verification

### Requirement: Reviewer challenge uses the compact current result contract
Reviewer SHALL perform independent, stage-specific challenge as review
behavior while submitting only the current compact result fields:
`pm_visible_summary`, `reviewed_by_role`, `passed`, `findings`, `blockers`,
`pm_suggestion_items`, and `contract_self_check`.

#### Scenario: Reviewer finds a hard current-stage gap
- **WHEN** original intent, a hard requirement, required evidence, workstream
  completeness, semantic non-downgrade, role authority, or current-stage
  quality is not established
- **THEN** Reviewer MUST return the gap through existing `findings` and
  `blockers`
- **AND** Reviewer MUST NOT downgrade the hard gap to a suggestion or repair
  the subject itself

#### Scenario: Reviewer finds a higher-standard opportunity
- **WHEN** the current hard contract is satisfied but a useful quality,
  simplicity, or optimization opportunity remains
- **THEN** Reviewer MUST use `pm_suggestion_items` as PM decision support
- **AND** the suggestion MUST NOT manufacture a Runtime blocker by itself

#### Scenario: Deleted challenge object is submitted
- **WHEN** a review result contains `independent_challenge` or another retired
  broad review object
- **THEN** Runtime MUST reject the field as deleted and forbidden
- **AND** no prompt, model, fake-AI positive fixture, compatibility reader, or
  fallback family may require or accept it as successful output

#### Scenario: Reviewer uses generic pass prose
- **WHEN** a repository-owned Reviewer fixture omits the delivered stage focus,
  task-specific challenge, required reads, or direct evidence and only repeats
  generic mechanical or score-optimization prose
- **THEN** the fake/model oracle MUST classify it as known-bad evidence
- **AND** it MUST NOT support Reviewer pass or parent confidence
