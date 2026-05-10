# FlowPilot PM Suggestion Disposition Plan

## Purpose

Unify reviewer, worker, and FlowGuard officer suggestions under one
Project-Manager-owned disposition loop without flattening role authority.

Current state already routes reviewer findings, worker/officer `PM Note`
content, and FlowPilot skill-improvement observations toward PM attention.
The gap is that these channels are not yet normalized into one run-scoped
ledger with explicit PM disposition and closure.

## Optimization Checklist

| Step | Optimization | Concrete Change | Done When |
| --- | --- | --- | --- |
| 1 | Model first | Add a FlowGuard model for PM suggestion intake, classification, disposition, and closure before protocol/runtime edits. | Hazard cases fail for unsafe plans, the happy path passes, and results are written under `simulations/`. |
| 2 | Unified suggestion item | Define one `PM Suggestion Item` shape for reviewer, worker, process-officer, and product-officer suggestions. | Templates/cards use the same fields for source role, classification, evidence refs, PM disposition, and closure state. |
| 3 | Run-scoped ledger | Add `.flowpilot/runs/<run-id>/pm_suggestion_ledger.jsonl` as the canonical run-local suggestion ledger. | State/run templates and schema docs include the ledger path and purpose. |
| 4 | Preserve authority differences | Keep reviewer/officer gate authority distinct from worker advisory notes. | Reviewer hard blockers can block only when minimum gate standard is not guaranteed; workers cannot block; formal officer model blockers stay gate-bearing. |
| 5 | PM disposition options | Require PM to choose one disposition for each suggestion: adopt now, repair/reissue, mutate route, defer to named node, reject with reason, waive with authority, stop for user, or record for FlowPilot maintenance. | PM cards and output contracts require disposition fields before affected gate/node closure. |
| 6 | Gate closure rule | Block current gate/node closure while current-gate blockers remain unresolved. | Runtime/model/tests reject completion with open `current_gate_blocker` items. |
| 7 | Deferred item binding | Require future-route suggestions to name a downstream node or gate. | Tests/model reject vague “do later” dispositions without a target. |
| 8 | Nonblocking separation | Keep FlowPilot skill-maintenance observations nonblocking and separate from current project acceptance. | Skill-improvement items can be recorded for maintenance without blocking current project completion. |
| 9 | Runtime/card propagation | Update reviewer cards, worker/officer packet templates, PM phase cards, and output contracts so suggestion items can be produced and consumed uniformly. | Card coverage and output-contract tests verify the new fields and authority language. |
| 10 | Local sync only | After validation, sync the repository-owned skill to the local installed FlowPilot skill, but do not push to GitHub. | Local install check/audit passes; git has local changes only. |

## Risk And Bug Checklist

| Risk ID | Possible Bug From This Change | Why It Matters | FlowGuard Must Catch |
| --- | --- | --- | --- |
| R1 | Reviewer hard blocker is downgraded to a soft note. | A gate may close while minimum standard is not guaranteed. | Any `current_gate_blocker` without repair, recheck, waiver, stop, or user decision must prevent gate closure. |
| R2 | Reviewer can block for pure preference or “nice to have”. | The route can become overblocked and too heavy. | Reviewer blocker authority is valid only for unmet hard requirement, missing proof, semantic downgrade, unverifiable acceptance, role-boundary failure, or protocol violation. |
| R3 | Worker advisory note is treated as gate approval or gate blocker. | Workers would gain reviewer/PM authority by accident. | Worker-origin suggestions must remain PM-decision-support until PM classifies them. |
| R4 | Officer tool/model improvement suggestion blocks project completion. | FlowPilot maintenance work could derail the user’s current project. | `flowpilot_skill_improvement` dispositions remain nonblocking unless PM classifies a true current-project blocker separately. |
| R5 | PM closes a node without disposing all relevant suggestions. | Suggestions can disappear in reports. | Node/gate closure requires all current-scope suggestion items to have PM disposition. |
| R6 | PM defers a suggestion without naming a target node/gate. | “Later” becomes untraceable. | `defer_to_named_node` requires a downstream node/gate id and keeps the item open until that boundary. |
| R7 | PM rejects or waives a suggestion without rationale/authority. | The process becomes arbitrary and unreviewable. | `reject_with_reason` requires reason; `waive_with_authority` requires authorized role, reason, and evidence/alternative handling. |
| R8 | Route mutation uses stale suggestion/evidence state. | Later route decisions may rely on superseded evidence. | `mutate_route` must record route version impact and stale-evidence handling before further work. |
| R9 | Suggestion ledger leaks sealed packet/result body content. | It violates the prompt-isolated packet runtime. | Ledger entries may reference evidence paths/envelopes only, never sealed body content. |
| R10 | Suggestion handling duplicates existing skill-improvement reporting. | Two maintenance systems can diverge. | FlowPilot maintenance suggestions link to the existing skill-improvement report path instead of replacing it. |
| R11 | Simple tasks are overburdened with heavy suggestion ceremony. | FlowPilot becomes slower for small gates. | Empty/no-suggestion cases stay lightweight and do not require bulky reports. |
| R12 | PM accepts current-gate blocker after repair without reviewer recheck. | Repair evidence may be self-approved. | Blocking reviewer-origin current-gate issues require same review class recheck or authorized stop/waiver. |

## FlowGuard Modeling Requirements

The new model must include:

- suggestion source roles: reviewer, worker, process officer, product officer;
- classifications: `current_gate_blocker`, `current_node_improvement`,
  `future_route_candidate`, `nonblocking_note`, and
  `flowpilot_skill_improvement`;
- PM dispositions: `adopt_now`, `repair_or_reissue`, `mutate_route`,
  `defer_to_named_node`, `reject_with_reason`, `waive_with_authority`,
  `stop_for_user`, and `record_for_flowpilot_maintenance`;
- closure states: open, pending repair, deferred, closed, blocked;
- authority constraints for reviewer, worker, and officer-origin items;
- sealed-body exclusion from ledger records;
- happy-path scenarios and hazard scenarios matching the risk checklist above.

## Implementation Order

1. Add `simulations/flowpilot_pm_suggestion_disposition_model.py`.
2. Add `simulations/run_flowpilot_pm_suggestion_disposition_checks.py`.
3. Run hazard checks and happy-path checks; revise the model until it catches
   R1-R12 and accepts the intended plan.
4. Add schema/template docs for `pm_suggestion_ledger.jsonl` and suggestion
   item entries.
5. Update PM/reviewer/worker/officer cards and packet templates to produce or
   consume suggestion items.
6. Add output-contract/card coverage tests.
7. Update router/runtime only where needed to index or enforce ledger closure.
8. Run targeted tests after each implementation slice.
9. Run full relevant validation and local install sync.

## Validation Plan

Targeted validation:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python simulations/run_flowpilot_pm_suggestion_disposition_checks.py --json-out simulations/flowpilot_pm_suggestion_disposition_results.json
python -m pytest tests/test_flowpilot_card_instruction_coverage.py tests/test_flowpilot_output_contracts.py tests/test_flowpilot_router_runtime.py -q
python scripts/check_install.py
```

Broader validation after integration:

```powershell
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/install_flowpilot.py --sync-repo-owned --json
python scripts/audit_local_install_sync.py --json
python scripts/install_flowpilot.py --check --json
```

Do not push to GitHub as part of this change.
