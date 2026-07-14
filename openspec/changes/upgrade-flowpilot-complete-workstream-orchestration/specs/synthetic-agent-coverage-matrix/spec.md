## ADDED Requirements

### Requirement: Synthetic coverage uses the canonical opened-packet responder
The synthetic agent coverage matrix SHALL bind each new complete-workstream, ordinary-material-work, and skill-inventory semantic profile to `ContractDrivenFakeAIResponder.from_open_packet_result` and the real packet/open/submit/review route.

#### Scenario: Profile bypasses canonical responder
- **WHEN** a new semantic fake response is produced from a standalone dictionary or alternate fake result family
- **THEN** the coverage gate SHALL fail the profile as non-canonical.

### Requirement: Coverage matrix reconciles finite universe states
The synthetic coverage matrix SHALL expose declared, applicable, excluded, generated, selected, executed, passed, failed, stale, and proof-backed counts and ids without conflating them.

#### Scenario: Parent receipt overstates proof
- **WHEN** a parent matrix claims more proof-backed cases than its current child execution artifacts support
- **THEN** the matrix gate SHALL fail and identify the overstated cases.

### Requirement: Synthetic workstream branches include semantic negatives and repair
The matrix SHALL cover complete-plan pass, missing/vague plan, incomplete required step, contradictory completion, stale evidence, unintegrated delegation, unauthorized FlowGuard self-approval, PM sub-9 disposition, and corrected retry branches.

#### Scenario: Shallow role result reaches review
- **WHEN** Runtime accepts a mechanically valid but semantically shallow plan report
- **THEN** the synthetic trace SHALL prove Reviewer detects the gap and the existing PM repair/reissue path can reach a corrected recheck.
