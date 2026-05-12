# FlowPilot PM Package Absorption Upgrade Plan

## Risk Intent Brief

This change moves ordinary worker package results out of the reviewer's default inbox. FlowGuard must prove the new protocol before runtime code changes: PM-issued work packages return to the Project Manager first, the PM records a disposition, and reviewers inspect only formal PM-built gate packages at protected route, node, material, research, and closure boundaries.

The protected harm is authority drift: the reviewer silently becoming the PM's receiving clerk, PM decisions being bypassed by direct worker-to-reviewer routing, or the cleanup accidentally removing reviewer hard gates that still protect product usefulness, route soundness, node acceptance, and final completion.

## Optimization Checklist

| ID | Optimization | Current behavior to replace | Target behavior | Primary files/models |
| --- | --- | --- | --- | --- |
| O1 | Add one common PM package-result disposition rule | Current-node, material-scan, and research worker results route directly to `human_like_reviewer`; PM role-work already returns to PM | Every PM-issued worker package result returns to `project_manager`; PM records `absorbed`, `rework_requested`, `canceled`, `blocked`, or `route_or_node_mutation_required` | New PM package FlowGuard model; router contract bindings; result-envelope contracts |
| O2 | Remove raw worker-package review as a normal reviewer job | Reviewer receives raw current-node/material/research result bodies before PM has accepted them | Reviewer receives only a PM-built formal gate package; raw worker reports remain PM intake material | Router relay actions; reviewer cards; packet ledger expectations |
| O3 | Preserve reviewer hard gates | A naive cleanup could remove useful reviewer checks together with noisy package checks | Reviewer remains mandatory for startup facts, material sufficiency, product architecture, root contract, child-skill manifest, route challenge, node acceptance plan, node completion gate, parent backward replay, evidence quality, and final backward replay | Router wait states; reviewer cards; meta/capability/router-loop models |
| O4 | Split material/research intake from material/research gate review | Material-scan and research results go directly to reviewer for sufficiency/source checks | Worker result returns to PM; PM absorbs or rejects it; PM then builds material or research gate evidence when the result will influence a protected decision | Material/research cards, contracts, control-plane model |
| O5 | Update resume/continuation paths | Existing or fresh worker results found during resume route directly to reviewer | Resume routes existing/fresh worker results to PM disposition first; only PM-built gate packages reach reviewer | Resume model and launcher/router status transitions |
| O6 | Update tests and runtime prompts together | Cards may keep telling roles to use old events even if router logic changes | Cards, contracts, manifest entries, tests, and FlowGuard hazards all use the same PM-first vocabulary | Runtime kit cards/templates, test suite, event/contract checks |
| O7 | Keep legacy state readable without treating it as current proof | Existing runs may contain `*_relayed_to_reviewer` flags | Legacy flags are audit history; next advancement requires PM disposition or a formal PM gate package under the new rule | Router state migration/compatibility checks |
| O8 | Sync safely after validation | Repo source and installed FlowPilot skill can drift | After tests pass, sync installed local skill from repo source and make a local git commit only; do not push to GitHub | `scripts/install_flowpilot.py`, local git |

## Bug-Risk Coverage Matrix

| Risk ID | Possible bug introduced by this upgrade | Required FlowGuard catch | Planned executable evidence |
| --- | --- | --- | --- |
| R1 | Worker result still routes directly to reviewer for current-node/material/research | Fail if a raw PM-issued worker result reaches reviewer before PM disposition and PM gate package creation | `flowpilot_pm_package_absorption_model.py` hazard: `raw_worker_result_relayed_to_reviewer` |
| R2 | PM can complete a node after absorbing a result but before reviewer node-completion gate | Fail if node completion happens without PM gate package plus reviewer pass | PM package model and router-loop model hazards |
| R3 | PM uses a worker result as formal evidence without recording disposition | Fail if result is used in route/node/material/research evidence before PM disposition | PM package model hazard: `formal_evidence_from_undispositioned_result` |
| R4 | Reviewer starts reviewing a raw worker result instead of a PM-built gate package | Fail if reviewer gate starts without `pm_gate_package_written` | PM package model hazard: `reviewer_started_without_pm_gate_package` |
| R5 | Cleanup removes mandatory reviewer gates for product architecture, route, node plan, or final replay | Fail if critical gate is marked passed/completed without reviewer participation | PM package model critical-gate hazards plus meta/capability checks |
| R6 | Resume path sends existing or fresh worker result to reviewer first | Fail if resume worker result is routed to reviewer before PM disposition | Resume model update plus PM package model hazard: `resume_result_direct_to_reviewer` |
| R7 | Material/research direct-source checks disappear entirely | Fail if material/research result affects product/route decisions without PM absorption and a formal reviewer gate when required | PM package model material/research hazards plus capability model updates |
| R8 | Controller reads or summarizes sealed packet/result bodies while changing relays | Fail if controller body access appears in PM-first flow | Existing router-loop/control-plane invariants plus PM package model hazard |
| R9 | Old `*_relayed_to_reviewer` flags are accepted as fresh evidence after the protocol change | Fail if legacy direct-review flags satisfy PM disposition or gate pass | PM package model hazard: `legacy_reviewer_relay_used_as_current_acceptance` |
| R10 | PM disposition has a hidden "forward raw package to reviewer" escape hatch | Fail if PM disposition outcome causes raw package review rather than a formal gate package | PM package model hazard: `pm_forwarded_raw_package_to_reviewer` |
| R11 | Contracts, cards, and router bindings disagree on `next_recipient` | Fail through contract/event checks or direct tests when runtime expects reviewer while contracts require PM | Event contract checks, router runtime tests, contract registry checks |
| R12 | Local installed FlowPilot skill remains stale after repo change | Fail final sync audit if installed skill content does not match repo-owned source | install sync/check commands |

## Implementation Order

1. Create or update FlowGuard model artifacts for PM-first package absorption and reviewer gate preservation.
2. Run negative hazards to prove the model catches R1-R10 before trusting a green plan.
3. Run the safe PM-first plan through the model and update existing router-loop, resume, control-plane, meta, and capability models where they still encode reviewer-first package routing.
4. Update runtime contracts and result-envelope recipient rules for current-node, material-scan, and research worker results.
5. Update router actions, flags, event names, and compatibility handling so worker results relay to PM and PM disposition gates formal reviewer packages.
6. Update cards/templates so PM, workers, and reviewers receive the same protocol instructions.
7. Run focused tests after each batch, then the strongest practical full verification.
8. Sync the local installed FlowPilot skill from the repository and create a local git commit; leave remote GitHub untouched.
