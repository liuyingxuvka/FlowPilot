# FlowPilot Control Transaction Registry Plan

Date: 2026-05-12

## Purpose

FlowPilot already has three strong control tables:

- event capability facts for whether a Router event is executable;
- output contract bindings for which role output may emit which Router event;
- repair transaction records for control-blocker repairs and rechecks.

The architecture problem is that these tables can still be consulted in
separate places. The fix is to promote them into one structural control plane:
every route advancement, packet dispatch, result absorption, reviewer gate,
control-plane reissue, repair, or route mutation must be evaluated as a registered control
transaction before it can mutate run state.

This is not a temporary compatibility layer. It is the new bottom-level
authority for FlowPilot control writes. The existing three tables remain as
sub-registries referenced by the transaction registry; their facts are not
duplicated.

## Optimization Sequence

| Order | Optimization point | Concrete work | FlowGuard proof before runtime edit | Runtime done evidence |
| --- | --- | --- | --- | --- |
| 1 | Freeze transaction architecture | Record the transaction types, referenced sub-registries, commit targets, and non-goals in this plan. | Plan risks are represented in `flowpilot_control_transaction_registry_model.py`. | `docs/flowpilot_control_transaction_registry_plan.md` exists and is install-checked. |
| 2 | Add the control transaction model | Model `route_progression`, `packet_dispatch`, `result_absorption`, `reviewer_gate_result`, `control_blocker_repair`, `control_plane_reissue`, `route_mutation`, and `legacy_reconcile`. | Valid scenarios accept; every risk in the bug checklist rejects with a named failure. | New runner writes `flowpilot_control_transaction_registry_results.json`. |
| 3 | Add the registry artifact | Add one runtime-kit registry that names each transaction type and references existing contract, event capability, repair transaction, packet authority, and commit-target requirements. | Source checks reject missing transaction rows, bad references, and unsafe outcome policies. | `control_transaction_registry.json` is present in repo and installed skill. |
| 4 | Make repair decisions use the registry | PM control-blocker repair must validate the `control_blocker_repair` transaction row before writing the repair decision, transaction record, allowed events, blocker record, or indexes. | Model rejects repair without transaction registration, collapsed outcomes, parent repair leaf events, and partial commits. | Router path for `pm_records_control_blocker_repair_decision` validates transaction row before commit. |
| 5 | Make packet/result authority a transaction gate | Packet result absorption must not unlock continuation unless packet ledger role-origin checks and completed-agent checks pass. | Model rejects packet evidence accepted with missing role origin or invalid completed agent. | Router and source checks expose packet authority as a required transaction fact. |
| 6 | Add legacy reconcile/quarantine | Existing live artifacts that predate the registry, such as collapsed repair outcome tables, are not continued. They are classified as invalid legacy transactions requiring PM reissue/repair. | Model rejects old bad transactions being used as permission to continue. | Mesh live projection and targeted Router checks classify stale invalid transactions as blocked, not safe. |
| 7 | Integrate install, smoke, and coverage sweep | Add plan/model/registry/result to check-install and smoke; classify the new model as strong coverage. | Coverage sweep parses the new runner and reports findings if any transaction risk is live. | `check_install.py`, coverage sweep, and fast smoke pass. |
| 8 | Sync local install and local git only | After all checks pass, sync the repository-owned installed skill and commit locally. | Adoption log records commands, findings, skipped GitHub push, and residual blindspots. | `install_flowpilot.py --sync-repo-owned --json`, audit/check, local git stage/commit succeed. |

## Bug and Regression Checklist

| Risk id | Possible bug | Why it matters | Required FlowGuard catch |
| --- | --- | --- | --- |
| T1 | A control mutation uses an unregistered transaction type. | A new path can bypass the unified authority. | Reject `unregistered_transaction_type`. |
| T2 | A contract-bound output is accepted without event capability validation. | A role can emit a well-formed but non-executable event. | Reject `contract_pass_event_capability_missing`. |
| T3 | An event-capability pass is accepted without the output contract binding. | A Router event can be emitted by the wrong role or output type. | Reject `event_pass_contract_missing`. |
| T4 | Packet/result evidence is accepted without role-origin audit. | Wrong-role or stale packet evidence can unlock continuation. | Reject `packet_authority_missing`. |
| T5 | `completed_agent_id` is a role key or does not map to the completing role. | A role name can masquerade as a real agent identity. | Reject `completed_agent_invalid`. |
| T6 | Repair success, blocker, and protocol-blocker outcomes share one event. | Failed repairs can look like success. | Reject `collapsed_repair_outcomes`. |
| T7 | A control-blocker repair commits without a repair transaction. | PM repair becomes a one-off write instead of a durable transaction. | Reject `repair_without_transaction`. |
| T8 | Parent/backward repair targets a leaf-only current-node event. | Parent composition can jump into child-local packet dispatch. | Reject `parent_repair_leaf_event`. |
| T9 | A transaction writes only part of the state surface. | Frontier, packet ledger, blocker index, and status can disagree. | Reject `partial_commit_targets`. |
| T10 | Active blocker exists while the transaction reports safe continuation. | A blocked run can be treated as green. | Reject `active_blocker_marked_green`. |
| T11 | Old invalid repair transactions are used as current permission. | Previously persisted bad state can bypass new checks. | Reject `legacy_bad_transaction_continues`. |
| T12 | Registry rows reference nonexistent contract ids or events. | The registry advertises impossible transactions. | Reject `registry_reference_missing`. |
| T13 | Route mutation commits without stale-evidence and route-version policy. | Old approvals can remain valid after structural change. | Reject `route_mutation_without_stale_policy`. |
| T14 | Reviewer blocker/protocol output uses a success-only event. | Non-success review outcomes can close as success. | Reject `reviewer_non_success_uses_success_event`. |
| T15 | A transaction claims atomic commit but omits a required target. | The run can be left half-updated after a crash or partial branch. | Reject `atomic_commit_target_missing`. |
| T16 | Control-plane reissue is judged only by the original event card flag. | A valid same-role reissue can be blocked before the reissue packet is delivered. | Accept `valid_control_plane_reissue`; reject `control_plane_reissue_without_delivery_authority`. |

## Registry Shape

The registry should stay compact. Each row says what the transaction requires;
it does not duplicate contract schemas, event definitions, or repair
transaction bodies.

| Field | Meaning |
| --- | --- |
| `transaction_type` | Stable transaction name. |
| `producer_roles` | Roles allowed to initiate it. |
| `output_contract_ids` | Contract ids that can submit it, when role output is required. |
| `router_events` | Router events associated with the transaction. |
| `event_usages` | How events are used: `wait`, `rerun_target`, `repair_outcome`, or `recorded_event`. |
| `packet_authority_required` | Whether packet ledger role-origin and agent checks are mandatory. |
| `repair_transaction_required` | Whether a repair transaction record is mandatory. |
| `outcome_policy` | `none`, `single_event`, or `three_distinct_outcomes`. |
| `commit_targets` | State surfaces that must be committed together. |
| `legacy_policy` | How stale pre-registry artifacts are handled. |

## Required Transaction Types

| Transaction type | Uses contract registry | Uses event capability | Uses repair transaction | Uses packet authority | Commit targets |
| --- | --- | --- | --- | --- | --- |
| `route_progression` | yes | yes | no | no | frontier, run_state, status_summary |
| `packet_dispatch` | yes | yes | no | no | packet_ledger, run_state, status_summary |
| `result_absorption` | yes | yes | no | yes | packet_ledger, run_state, status_summary |
| `reviewer_gate_result` | yes | yes | no | conditional | run_state, blocker_index, status_summary |
| `control_blocker_repair` | yes | yes | yes | conditional | repair_transaction, blocker_index, run_state, status_summary, optional packet_ledger/frontier |
| `control_plane_reissue` | no | yes | no | audit existing only | blocker_index, run_state, status_summary |
| `route_mutation` | yes | yes | conditional | no | route, frontier, stale_evidence, run_state, status_summary |
| `legacy_reconcile` | no | yes | yes | yes | blocker_index, repair_transaction_index, status_summary |

## Non-Goals

- Do not create a second copy of every contract or event row.
- Do not add a new review phase.
- Do not make install checks fail merely because the active run is correctly
  classified as blocked.
- Do not delete old run artifacts during reconcile; classify and block them.
- Do not push to GitHub during this task.
