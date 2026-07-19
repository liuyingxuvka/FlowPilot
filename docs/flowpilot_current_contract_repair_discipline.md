# FlowPilot Current-Contract Repair Discipline

This document is mandatory maintenance guidance for FlowPilot contract,
runtime, prompt, model, test, install, and repair work.

FlowPilot must remain a current-contract runtime with one clear path per
behavior. A bug fix is not allowed to add broad new fields, compatibility
aliases, fallback parsers, optional alternate branches, or role-specific
sub-protocols merely because one packet failed. The default repair is to find
the root contract mismatch, shrink or relocate the wrong requirement, and cover
the result with model and test evidence.

## Role Boundaries

- Runtime/router owns mechanical validity only: schema, packet family, current
  run, current packet/result/node ids, path/hash presence, fixed blocker enum
  membership, fixed next-action mapping, and rejection of old fields or
  unsupported paths.
- FlowGuard operator owns process and state modeling. It models the current
  artifact, writes model details to the packet-owned run-local evidence file,
  self-repairs small model/test gaps inside that evidence surface when it can,
  and returns only PM-facing summary, modeled boundary, blockers, suggestions,
  and contract self-check in the result body.
- Reviewer owns human quality review. Reviewer may block, but only with a
  fixed blocker class allowed for the current subject family. Reviewer does
  not become Runtime and does not demand future-stage terminal evidence from an
  early packet.
- PM owns route, repair, absorption, waiver, stop, and completion decisions.
  PM writes the current-stage package and absorbs FlowGuard/Reviewer outputs;
  PM does not pre-fill FlowGuard model internals or maintain duplicate test
  matrices for downstream roles.

## Field And Contract Rules

Every behavior-bearing field touched by a repair must have exactly one
disposition:

- keep: belongs to exactly one current packet/result family;
- move: belongs to a named later or different owner, and is forbidden in the
  current family;
- delete: unsupported in the current contract and rejected when submitted.

The source of truth is
`skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py`
together with
`skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py`.
Prompt cards and `runtime_kit/contracts/contract_index.json` must not describe
requirements that contradict those rows.

Before adding any field, table, packet kind, prompt channel, role, repair
state, ledger, or validation layer, answer all of these in the code review or
change notes:

- Which observed blocker, loop, stale-evidence hazard, or unsupported path does
  this prevent?
- Can an existing packet, result, gate, blocker, route node, or run-local
  evidence file express the same repair?
- Is this mechanical validation owned by Runtime/router instead of FlowGuard
  or Reviewer?
- Does the new state have one owner, one commit point, one cleanup or terminal
  disposition, and a negative test?

If any answer is weak, reduce the repair instead of expanding the contract.

## Package And Blocker Coverage

Current regression coverage must enumerate every mainline package family:

- `task.high_standard_contract`
- `task.discovery`
- `task.skill_standard`
- `task.planning`
- `task.node_acceptance_plan`
- `task.node`
- `flowguard_check.post_result`
- `review.any_current_subject`
- `pm_repair_decision.pm_repair_decision`
- `pm_disposition.node_pm_disposition`
- `task.parent_backward_replay`
- `review.terminal_backward_replay`

Every supported blocker class must map to exactly one fixed next action and
exactly one repair packet contract. The repair contract must name the current
source packet/result/node ids, required opened-body receipt or evidence refs,
owner role, payload fields, and return gate. Repeated repair packets must carry
the original blocker id, prior repair packet/result ids, prior evidence refs,
failed recheck report id, prior failure reason, current blocking report id, new
repair delta, and return gate. A second repair must not forget the first repair
materials.

## Repair Topology Rules

PM owns repair topology selection. A substantive blocker records the problem,
evidence, and recommended repair direction; it does not decide PM's repair
branch. Runtime routes PM-owned blockers into the current
`pm_repair_decision` packet, then applies the existing repair topology selected
by PM before inventing a new one:

- current packet/node defect can use `repair_current_scope`;
- parent composition defect can use `repair_parent_scope` with
  `repair_parent_scope_contract`, `inherit_existing_children=true`, and active
  `repair_child_specs[]`; inherited old children/results are history only;
- route/node too broad, too shallow, wrongly ordered, or structurally wrong at
  node entry can use `redesign_route` with a replacement parent/module and child
  nodes. Runtime stages the route effect, FlowGuard simulates the current route
  plan, PM absorbs that FlowGuard result, and Reviewer checks the PM absorption
  package;
- terminal closure defect can use a terminal supplemental repair contract on
  the selected continuing repair branch, then terminal backward replay again.

Do not create a separate repair family when one of these paths already models
the issue.

Every PM decision that continues repair work uses the same gate sequence before
Runtime commits the effect or opens the resulting repair work:

1. PM submits the current `pm_repair_decision` result with the fixed
   `decision`, `target_blocker_id`, `next_action`, required repair contract,
   and any required route or parent/terminal supplemental payload.
2. Runtime stages the repair effect in `pm_decision_gates`; it does not apply
   the route mutation or release the repair work as accepted progress yet.
3. FlowGuard checks the staged current effect and consumes the blocker-bound
   repair obligations.
4. PM absorbs the FlowGuard result in `pm_flowguard_acceptance`.
5. Reviewer checks the PM-absorbed current decision package.
6. System validation and system closure record the final gate evidence.
7. Runtime applies the staged effect and only then opens or advances the
   resulting repair work.

This sequence applies whenever PM chooses a continue-repair decision.
`repair_current_scope`, `repair_parent_scope`, and `redesign_route` all use
it. `stop_for_user` and an allowed authority waiver are terminal PM
dispositions, not continue-repair paths.

## Prompt And Test Hygiene

Prompt cards may instruct roles to think rigorously, inspect evidence, and
challenge weak work, but valid result bodies must stay compact and current.
Do not reintroduce old broad fields such as Reviewer challenge objects,
FlowGuard model-detail arrays, PM mirror matrices, terminal segment review
arrays, or parallel PM disposition arrays as successful output fields.

Old names may remain only in deleted/forbidden lists, negative tests, or
historical evidence labels. If an old name is still present in a prompt,
successful fixture, runtime compatibility read, generated contract, or positive
model obligation, remove it or prove that it is the current canonical name.

After any non-trivial repair, run a deleted-field search across runtime,
runtime-kit cards, contract index, tests, and simulations. Each hit must be
classified as one of:

- forbidden/deleted contract entry;
- negative test or known-bad case;
- historical evidence label;
- current valid field.

Any other hit is contract residue and must be removed before claiming done.

## Test Evidence Applicability

The canonical repository snapshot is provenance, not a blanket invalidation
switch. A changed snapshot fingerprint, FlowGuard package version, line-ending
transport, generated result, report, receipt, or progress log must not by
itself rerun every test owner.

Every background validation owner has one current applicability identity made
from its exact command, test source, tested artifacts, declared dependencies,
environment, covered inputs, obligations, and MTA evidence subjects. The
current impact planner has exactly three outcomes:

- `reuse`: every applicability component still matches and the same owner has
  a terminal passing proof plus a current `TestResultReuseTicket`;
- `execute`: the owner's own applicability identity changed or it has no
  reusable current proof;
- `blocked`: a changed governed source cannot be mapped unambiguously, the
  named previous v4 manifest or SHA-256 identity is missing/wrong, or the
  execution identity became stale.

There is no fourth outcome that converts `blocked` into run-all. The first v4
release uses one explicit `--seed-baseline`; later executions must name the
exact previous v4 manifest and its SHA-256. Old manifests, aggregate-only
proofs, global-fingerprint equality, newest-run discovery, and repo-root
discovery are not alternate evidence paths.

The background supervisor freezes the impact plan before launching exactly
the `execute` owners, carries forward exactly the `reuse` owners, and verifies
owner inputs again at process start, process exit, and supervisor closure.
Timeout or interruption evidence is invalid until the exact descendant
process tree is confirmed empty. Generated outputs never refresh source
authority or recursively invalidate their own producers.

Shared execution infrastructure is owned separately from the behavior payload
it launches. A payload command that uses `run_flowguard_background.py` keeps
the wrapper itself and the nested model/test import closure in its owner
identity, but it does not inherit the wrapper's test-tier, impact-planning, or
artifact-classification imports. Those imports belong to the current
`test_tier_runner` proof. When replacing a former over-broad identity, an
existing payload proof may be retained only by a strict scope-reduction proof:
the command, environment, obligations, evidence subjects, and every retained
input fingerprint are identical; the current inputs are a proper subset; and
every removed input is an actual wrapper import transferred to the exact
infrastructure owner. This is the single current ownership rule, not a legacy
identity reader or fallback.

A full validation is reserved for one stable integration/release snapshot or
for a change to the explicitly declared shared validation control plane. Run
focused affected checks while code is still changing. Do not repeatedly rerun
the full `all`, adversarial, Meta, or Capability owners after unrelated edits
or after a FlowGuard installation upgrade that is not part of their declared
identity.

## Historical Baseline

Historical successful runs are process-route evidence, not field-shape
authority. Use the successful mainline to preserve simple role order and
forward progress, then keep only the newer fields and gates that are necessary
for current behavior. Do not copy historical broad fields forward merely
because an old run happened to pass.
