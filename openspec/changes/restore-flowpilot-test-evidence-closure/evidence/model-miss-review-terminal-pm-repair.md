# Model-Miss Review: Terminal PM Repair Acceptance Ownership

## Observed Discrepancy

After the current handoff/checklist model and focused contract tests were green,
the public fake E2E terminal-repair path repeatedly produced
`mechanical_contract_blocked`. The current active acceptance registry contained
`acc-003`, while the PM repair checklist branch still used the registry's
static example route shape containing only `acc-001` and `acc-002`.

The result was a real no-progress loop: every reissued PM packet returned the
same incomplete route plan and never reached Reviewer or terminal closure.

## Why The Earlier Model Missed It

- The model proved field shape and branch presence, not dynamic owner coverage
  after the acceptance registry grew.
- Fake E2E had previously repaired the shape through a private helper, masking
  the handoff projection defect.
- No invariant connected `active_acceptance_item_ids` to the terminal PM repair
  branch `route_plan.nodes[].acceptance_item_ids`.

## Owning Repair

- Primary owner: runtime dynamic effective contract projection.
- Repair: `_project_current_pm_repair_contract` now projects every current
  active acceptance id onto the executable repair leaf and the supplemental
  repair item before the checklist is fingerprinted.
- No fallback: the fake responder still reads only the opened checklist; it
  does not inspect the ledger or reconstruct a private route shape.
- Terminal disposition: the dynamic branch either validates and advances or
  fails closed with current mechanical feedback.

## Same-Family Expansion

- Multiple active acceptance items, including ids absent from static examples.
- Terminal supplemental repair route redesign.
- PM route ownership validation.
- Reissue convergence and no-delta repetition.
- Checklist fingerprint protection after dynamic projection.

## Current Evidence

- Negative semantic blocker path:
  `test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker`.
- Repair convergence path:
  `test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion`.
- MTA obligation:
  `packet_result_family.dynamic_pm_repair_owner_projection`.
- BCL commitment:
  `commit.dynamic_pm_repair_owns_active_acceptance_items`.
- ObservedProblemBackfeed row:
  `terminal-pm-repair-static-acceptance-owner`.

This review closes the specific model miss only when the owning focused tests,
MTA, BCL, TestMesh, ModelMesh receipts, and release parents are current.
