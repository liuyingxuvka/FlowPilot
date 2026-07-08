## ADDED Requirements

### Requirement: Reviewer runtime gates are mechanical, not semantic

FlowPilot SHALL keep Reviewer result validation inside runtime limited to
mechanical current-contract checks. Runtime MUST NOT grade Reviewer prose,
keyword-match challenge language, or infer semantic review quality from text
patterns.

#### Scenario: Reviewer result has missing mechanical evidence
- **WHEN** a Reviewer result omits required fields, leaves required arrays
  empty, targets a noncurrent packet/result, lacks the current
  `accepted_result_id` binding, lacks authorized read/open receipts, or cites
  missing evidence paths
- **THEN** Runtime MUST reject or block the result through the existing
  mechanical contract
- **AND** Runtime MUST NOT repair the result by interpreting prose

#### Scenario: Reviewer text is shallow but mechanically shaped
- **WHEN** fake-AI or model coverage demonstrates a shallow Reviewer pass case
  with mechanically valid structure
- **THEN** that semantic weakness MUST be owned by Reviewer guidance,
  FlowGuard obligations, fake-AI replay, or D-card coverage
- **AND** Runtime MUST NOT add keyword, phrase, or semantic matching fields to
  judge prose quality

### Requirement: Reviewer pass authority requires current subject receipts

FlowPilot SHALL accept Reviewer pass authority only when existing mechanical
records prove the Reviewer was issued the current subject and opened the
authorized current material through the runtime path.

#### Scenario: Reviewer did not open the current result body
- **WHEN** a Reviewer result claims pass for a current accepted result
- **AND** the run-scoped packet/runtime ledgers do not prove authorized opening
  of that current result body or required current material
- **THEN** Runtime MUST reject or block the Reviewer result mechanically
- **AND** the gate MUST remain unresolved until current authorized-read
  evidence exists.

### Requirement: Reviewer prompts require active verification behavior

FlowPilot SHALL instruct every current Reviewer review packet/card to actively
inspect the reviewed work and evidence, run relevant focused tests or
FlowGuard/model checks when practical, compare the work against current
spec/model/contract obligations, and add or repair review-scope tests or
fixtures when that is necessary to prove a defect or prevent shallow approval.

#### Scenario: Reviewer packet omits active verification duty
- **WHEN** Runtime issues a Reviewer packet for a current review flow
- **THEN** the packet or referenced Reviewer card MUST tell Reviewer to open
  current work and evidence rather than relying on summaries
- **AND** it MUST tell Reviewer to run relevant tests, model checks, or
  FlowGuard checks when those checks are useful for the reviewed risk
- **AND** it MUST allow Reviewer to add or repair review-scope tests or
  fixtures when existing tests do not cover a material quality risk

#### Scenario: Reviewer active work stays within role boundary
- **WHEN** Reviewer identifies a production defect, missing implementation, or
  route-invalidating issue while actively verifying work
- **THEN** Reviewer MUST block or report through the existing Reviewer/PM
  repair path
- **AND** Reviewer MUST NOT directly accept, repair, or mutate production work
  outside the current authorized review/test evidence scope.
