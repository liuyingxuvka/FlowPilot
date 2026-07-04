## Why

FlowPilot can currently complete a run with strong process evidence while the
PM contract, reviewer challenge, node plan, or final replay has lost the user's
concrete original intent. This change tightens the existing prompt-card gates so
PM and Reviewer preserve source intent, acceptance slices, child-skill
standards, and final-artifact evidence without adding a parallel workflow or
asking runtime to judge semantic quality.

## What Changes

- Strengthen PM role and phase cards so PM must keep user intent as concrete
  acceptance rows instead of replacing it with generic "complete the user goal"
  wording.
- Strengthen Reviewer role and review cards so Reviewer blocks semantic
  dilution, vague contracts, missing source-intent comparison, existence-only
  evidence, and final-output drift using existing blocker and repair fields.
- Clarify FlowGuard operator wording so process/model evidence is not claimed
  as product-quality evidence by itself.
- Tighten child-skill selection and gate-manifest prompts so selected skills act
  as standards lenses inside the same FlowPilot route, not as separate
  domain-specific workflows.
- Tighten final ledger, evidence-quality review, terminal backward replay, and
  closure prompts so final closure starts from the delivered product and traces
  back to source requirements and accepted evidence.
- Add focused prompt-card regression tests and planning-quality/model-miss
  coverage for generic intent collapse, selected-skill standard loss,
  existence-only evidence, and ledger-only final replay.
- Keep runtime/router responsibility mechanical only: verify that the required
  reviews, packets, and ledgers exist and follow the current contract; do not
  add runtime semantic judging of whether a requirement is too vague.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-gate-review-standards`: reviewer gates must compare source intent,
  acceptance rows, and actual artifacts instead of relying on package shape or
  FlowGuard reports alone.
- `role-scoped-quality-repair-prompts`: role prompts must preserve quality
  repair boundaries while making PM/Reviewer responsible for source-intent and
  product-quality challenge.
- `role-child-skill-use`: child skills must be carried as role-scoped standards
  and evidence expectations inside existing PM, Reviewer, FlowGuard, and Worker
  gates.
- `flowpilot-prompt-boundary-policy`: shared prompt boundaries must keep
  runtime as mechanical authority and keep semantic quality with PM/Reviewer.
- `terminal-ledger`: terminal ledger and backward replay must close accepted
  source requirements against the delivered product, not just process records.

## Impact

- Affected prompt cards:
  - `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md`
  - `skills/flowpilot/assets/runtime_kit/cards/roles/flowguard_operator.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_product_architecture.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_selection.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_gate_manifest.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_node_acceptance_plan.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_evidence_quality_package.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_final_ledger.md`
  - `skills/flowpilot/assets/runtime_kit/cards/phases/pm_closure.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/root_contract_challenge.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/node_acceptance_plan_review.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/evidence_quality_review.md`
  - `skills/flowpilot/assets/runtime_kit/cards/reviewer/final_backward_replay.md`
- Affected tests and models:
  - prompt/card instruction coverage tests
  - planning-quality and reviewer-active-challenge FlowGuard checks
  - model-test alignment and install/sync checks as final validation
- No new dependencies, no release/publish/deploy action, and no runtime semantic
  evaluator.
