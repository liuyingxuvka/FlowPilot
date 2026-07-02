# formal-gate-review-standards Specification

## ADDED Requirements

### Requirement: FlowGuard Operator answers the work order, not final user quality

FlowGuard Operator SHALL answer the current FlowGuard work order and explicit blocker-bound check items. It SHALL NOT be treated as the final quality or user-intent judge.

#### Scenario: FlowGuard report checks only mechanics
- **WHEN** the current FlowGuard packet or work order requests subject-bound check items
- **AND** the report only checks field shape, hashes, current-contract mechanics, or role boundary
- **THEN** the report MUST be considered insufficient for that work order.

### Requirement: Reviewer blocks shallow repair and shallow evidence

Reviewer SHALL block when a gate depends on unresolved blocker obligations, shallow FlowGuard evidence, unread relevant ordinary materials, stale/superseded evidence, or existence-only proof for a hard quality claim.

#### Scenario: Reviewer sees a generic pass over concrete obligations
- **WHEN** PM, Worker, or FlowGuard outputs do not answer the concrete obligations that define the current gate
- **THEN** Reviewer MUST block using existing blocker and recommended-resolution fields.

### Requirement: Reviewer owns terminal quality and public user-intent replay

Reviewer SHALL use public user-intent artifacts, final artifacts, and relevant non-sealed work materials to judge whether final completion satisfies the user's current goal.

#### Scenario: Final artifact exists but quality or intent closure is unproven
- **WHEN** final replay proves file existence, hashes, or ledger cleanliness but does not prove user-intent and quality closure
- **THEN** Reviewer MUST return final blockers or required terminal repair.
