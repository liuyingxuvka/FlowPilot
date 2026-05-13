# Reviewer-Only Gate Simplification Plan

Date: 2026-05-13

## Decision

For the speed profile, `root_contract` and `child_skill_manifest` use
Reviewer-only default gates:

- Root contract: PM writes the contract, Reviewer passes it, PM freezes it.
- Child-skill manifest: PM writes the manifest, Reviewer passes it, PM
  approves it for route use.

Product FlowGuard Officer and Process FlowGuard Officer checks are removed from
these two default gates. PM may still use ordinary role-work consultation
elsewhere, but that consultation is not a required condition for either gate.

## Optimization Checklist

| Order | Optimization point | Current behavior | Target behavior | Main files |
| --- | --- | --- | --- | --- |
| 1 | Model reviewer-only root contract gate | Abstract models still require root contract Product Officer modelability before freeze. | FlowGuard models accept freeze after PM contract write and Reviewer pass only. | `simulations/flowpilot_reviewer_only_gate_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`, `simulations/prompt_isolation_model.py` |
| 2 | Model reviewer-only child-skill manifest gate | Abstract models still require Reviewer, Process Officer, Product Officer, then PM approval. | FlowGuard models accept PM approval after PM manifest write and Reviewer pass only. | `simulations/flowpilot_reviewer_only_gate_model.py`, `simulations/meta_model.py`, `simulations/capability_model.py`, `simulations/prompt_isolation_model.py` |
| 3 | Router root contract sequence | Router delivers `product_officer.root_contract_modelability` after Reviewer pass and waits for its event. | Router skips that card in the default sequence and lets PM freeze after Reviewer pass. | `skills/flowpilot/assets/flowpilot_router.py` |
| 4 | Router child-skill sequence | Router delivers `process_officer.child_skill_conformance_model` and `product_officer.child_skill_product_fit`, then waits for Product Officer before PM approval. | Router skips both cards and lets PM approve after Reviewer pass. | `skills/flowpilot/assets/flowpilot_router.py` |
| 5 | Prompt cards | PM cards still say Reviewer and Officer checks must pass. | PM cards say Reviewer must pass; Reviewer cards carry the default review burden. | `skills/flowpilot/assets/runtime_kit/cards/phases/pm_root_contract.md`, `skills/flowpilot/assets/runtime_kit/cards/phases/pm_child_skill_gate_manifest.md`, reviewer cards |
| 6 | Tests and compatibility | Tests expect officer cards in the default path. | Tests prove Reviewer remains required and officer cards are not emitted by default. Legacy officer events may remain accepted for old runs but cannot block new runs. | `tests/test_flowpilot_router_runtime.py`, simulation runners |
| 7 | Local install and git | Repo and installed skill can diverge after source edits. | Sync the local installed skill from repo, run local install audit, then commit locally without pushing GitHub. | `scripts/install_flowpilot.py`, `scripts/audit_local_install_sync.py`, local git |

## Bug/Risk Checklist

| Risk id | Possible bug caused by this optimization | FlowGuard must catch it by requiring/failing |
| --- | --- | --- |
| R1 | PM freezes root contract without Reviewer pass. | Root freeze requires PM contract write and Reviewer pass. |
| R2 | Router still waits for Product Officer before root freeze, so speed gain is fake. | Reviewer-only profile fails if Product Officer is required or default card is emitted. |
| R3 | Router emits removed root Product Officer card by default. | Reviewer-only profile fails when removed officer card emission is present. |
| R4 | PM approves child-skill manifest without Reviewer pass. | Child-skill approval requires PM manifest write and Reviewer pass. |
| R5 | Router still waits for Process Officer/Product Officer before child-skill approval. | Reviewer-only profile fails if Process/Product Officer is required. |
| R6 | Router emits removed child-skill officer cards by default. | Reviewer-only profile fails when either removed child-skill officer card is emitted. |
| R7 | Reviewer-only simplification drops root contract verifiability/modelability scrutiny entirely. | Reviewer checklist must cover verifiability, proof obligations, scenario coverage, and report-only downgrade rejection. |
| R8 | Reviewer-only simplification drops child-skill hard-standard/evidence scrutiny. | Reviewer checklist must cover skill standards, evidence obligations, approvers, skipped steps, and self-approval rejection. |
| R9 | Old officer events become silently necessary for new-run completion. | Reviewer-only success path must complete with no officer pass flags. |
| R10 | Route work starts before root contract freeze or child-skill manifest approval. | Route-ready state requires both PM root freeze and PM child-skill approval. |
| R11 | Removed gate bodies are merged into Controller or PM chat instead of staying role-scoped. | Reviewer-only model fails if role/body boundary isolation is not preserved; existing packet/body boundary models and Router tests remain in the validation suite. |
| R12 | Existing runs already mid-officer-gate break unexpectedly. | Reviewer-only model fails if legacy officer event compatibility is removed; runtime changes preserve legacy event handlers and only change default next-card sequencing. |
| R13 | Root freeze event no longer waits for Product Officer, but `_freeze_root_acceptance_contract` still requires `flowguard/root_contract_modelability.json`. | Reviewer-only model has a hidden-officer-artifact hazard; runtime tests must freeze with no root modelability file. |
| R14 | Child-skill PM approval no longer waits for officers, but `_approve_child_skill_manifest_for_route` still requires child-skill officer report files. | Reviewer-only model has hidden-officer-artifact hazards; runtime tests must approve with no child-skill officer files. |

## Required Model Sequence

1. Add or update FlowGuard model coverage for Reviewer-only root contract and
   child-skill manifest gates.
2. Prove each risk scenario above fails in the model.
3. Prove the target Reviewer-only success path passes without officer flags.
4. Only then edit Router, cards, docs, and tests.
5. After each implementation slice, run the narrow relevant tests before moving
   to the next slice.
