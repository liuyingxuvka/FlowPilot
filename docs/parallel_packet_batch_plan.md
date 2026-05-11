# Parallel Packet Batch Upgrade Plan

## Goal

Upgrade PM-authored work from single active packet/request channels to a
router-owned parallel packet batch. PM may issue one batch containing multiple
bounded packets for roles that can start now. Router records the full batch,
relays packets to the addressed roles, waits for every packet result, then
performs one batch-level review or PM absorption step before the route advances.

## Implementation Checklist

| Step | Area | Concrete Change | Done Signal |
| --- | --- | --- | --- |
| 1 | FlowGuard model | Add a dedicated parallel packet batch model covering batch registration, relay, result join, batch review, PM absorption, repair, and stage advance. | Model safe graph passes and known-bad hazards are detected. |
| 2 | Shared batch runtime | Add router helpers for a `parallel_packet_batch` index with `batch_id`, `batch_kind`, `join_policy`, `review_policy`, packet records, counts, and per-packet status. | One helper can register, load, relay, validate all results, and mark review/absorption for material, research, current-node, and PM role-work. |
| 3 | Material scan | Move the existing material `packets[]` path onto the shared batch index while keeping material-specific review rules. | Material scan records one batch, relays all packets, and relays all results to reviewer only after every result exists. |
| 4 | Research package | Replace single `worker_owner`/single packet behavior with `packets[]`. Allow worker and FlowGuard officer packets when the PM package needs parallel research/modeling. | Research relay can address multiple packet recipients and waits for all research/officer results before reviewer direct-source/model review. |
| 5 | Current node work | Replace the single current-node packet/write grant with a current-node batch and one grant per packet. | PM can register multiple current-node packets, Router tracks all grants, all results, and one batch review before PM node completion. |
| 6 | PM role-work requests | Replace single `active_request_id` with an active request batch containing multiple role-work packets. | PM may ask multiple roles for bounded advice; Router waits for all returned results before PM records one batch decision. |
| 7 | Reviewer flow | Add batch-level review contract fields: `batch_id`, `reviewed_packet_ids`, `packet_count`, `per_packet_findings`, and `overall_passed`. | Reviewer cannot pass a batch unless every required packet is opened and reviewed. |
| 8 | Prompt cards | Update PM, worker, officer, and reviewer cards to describe batch registration, direct-to-router returns, role busy/idle, and one batch join before stage advance. | No active prompt tells roles to return result envelopes through Controller or to advance after a single packet in a batch. |
| 9 | Tests | Add targeted runtime tests for material, research, current-node, PM role-work, officer packets, partial-result blocking, batch review blocking, and all-pass advance. | New targeted tests pass; existing router/model checks still pass. |
| 10 | Local sync | Refresh the locally installed FlowPilot skill from the repo and run local install audits. | `install_flowpilot.py --sync-repo-owned --json`, audit, and check commands pass; local git commit records the change. |

## Prompt Files To Update

| File | Required Update |
| --- | --- |
| `skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md` | Describe material scan as a batch. PM may include multiple worker packets; Router joins every result before material sufficiency review. |
| `skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md` | Replace single `worker_owner` guidance with `packets[]`. PM may include worker research and officer model packets in the same research batch. |
| `skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md` | Replace single current-node packet guidance with current-node batch guidance. All packet results must join and pass one batch result review before PM completes the node. |
| `skills/flowpilot/assets/runtime_kit/cards/phases/pm_role_work_request.md` | Replace one active request with one active request batch. PM records one disposition after all role-work results return. |
| `skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md` | Add PM-wide rule: issue only work that can start now; simultaneous packet registration means PM asserts the packets can run in parallel inside the current router-authorized scope. |
| `skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md` and `worker_b.md` | Clarify workers complete only their addressed packet and do not infer batch completion or route advancement. |
| `skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md` and `process_flowguard_officer.md` | Clarify officers may receive PM batch packets for bounded FlowGuard/modeling work, but cannot make PM decisions or reviewer approvals. |
| `skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md` | Add batch-review rule: review every packet result in the Router-supplied batch list and return one overall pass/block report. |

## Failure Modes FlowGuard Must Catch

| ID | Failure Mode | Required Detection |
| --- | --- | --- |
| F1 | Router advances after the first packet result instead of waiting for all results. | Invariant failure: stage advanced before batch joined. |
| F2 | Reviewer passes a batch after reviewing only part of the packet list. | Invariant failure: review passed without all packet ids reviewed. |
| F3 | Router gives a role a second packet while that role still has an open packet. | Invariant failure: busy role assigned another open packet. |
| F4 | PM emits duplicate packet ids or a duplicate active batch for the same stage. | Invariant failure: duplicate batch/packet registration accepted. |
| F5 | Old single-packet path bypasses the batch index. | Invariant failure: packet relayed or result accepted without batch membership. |
| F6 | Officer packet result is not counted in the batch join. | Invariant failure: batch joined while any officer packet is missing. |
| F7 | Controller reads or relays sealed body content instead of envelope metadata. | Invariant failure: sealed body boundary broken. |
| F8 | One packet blocks or fails, but the whole batch is still marked passed. | Invariant failure: batch passed with blocking packet. |
| F9 | Batch repair/reissue loses lineage from the original batch and packets. | Invariant failure: replacement batch lacks parent batch/packet lineage. |
| F10 | Prompt says batch parallelism exists while runtime remains single active request/packet. | Conformance failure: prompt/runtime capability mismatch. |
| F11 | Generic wait events still use one fixed producer role and reject the remaining batch member, for example waiting for worker B with an event formerly classified as worker A. | Invariant failure: dynamic batch wait rejected a valid remaining event producer role. |

## FlowGuard Risk Intent Brief

- Protected harm: route stages advancing from partial work, PM decisions from
  incomplete evidence, reviewer approval over only a subset of a parallel batch,
  Controller body access, role overload, and prompt/runtime drift.
- State to model: active batch, packet membership, role busy state, relay
  records, result records, reviewer coverage, PM absorption, repair lineage,
  dynamic wait producer binding, and route stage advancement.
- Side effects to model: packet relay, result receipt, reviewer batch report,
  PM batch disposition, and route advance.
- Hard invariant: every work path that may affect the route must be a member of
  exactly one active batch, and route advancement requires every packet in that
  batch to have returned, been reviewed when required, and not be blocked.
- Blindspot: the model is an abstract preflight. Runtime tests and prompt
  coverage checks remain required after implementation.
