# FlowPilot Process-Contract Binding Repair Plan

Date: 2026-05-11

## Risk Intent Brief

This repair closes a protocol class where a FlowPilot run can combine one
process lane with a different output contract, result recipient, or closure
event. The observed instance was a PM role-work repair packet that used the
current-node worker result contract. The broader protected harm is not that one
contract choice; it is any mismatch among process kind, initiator, target role,
output contract, result recipient, absorbing role, closure event, and event
producer.

Protected harms:

- Router must reject mismatched process/contract/event bindings before a packet
  or wait boundary is persisted.
- PM, worker, reviewer, and officer flows must not rely on role memory or
  later Controller compensation to repair a bad contract choice.
- Result recipients must come from the process contract, not from ad hoc role
  output choices.
- Closure events must be producible by the role currently asked to produce
  them, or the Router must first route to the correct producer.
- Existing valid flows such as current-node worker review, PM role-work
  requests, officer reports, material scan, research, resume decisions, and
  control-blocker repair must remain legal.

## Process Binding Table

| Process kind | Initiator | Target role class | Allowed contract family | Required result recipient | Absorbing role | Closure event family | Legal closure producer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `current_node_work` | `project_manager` through current-node packet registration | worker | `worker.current_node` | `human_like_reviewer` | reviewer first, then PM/node ledger | `current_node_reviewer_*_result` | `human_like_reviewer` |
| `pm_role_work_request` | `project_manager` | worker, reviewer, process officer, product officer | `pm.role_work_request` | `project_manager` | `project_manager` | `pm_records_role_work_result_decision` or a new PM-selected follow-up | `project_manager` |
| `officer_model_report` | `project_manager` or Router gate | process/product officer | `officer.model_report` or `officer.model_miss_report` | `project_manager` | `project_manager` | PM decision event that consumes the report | `project_manager` |
| `reviewer_result_review` | Router after worker current-node result | reviewer | `reviewer.review` | Router/PM metadata only | reviewer | `current_node_reviewer_*_result` | `human_like_reviewer` |
| `material_scan` | PM material scan package | worker | `worker.material_scan` | `human_like_reviewer` | reviewer, then PM material absorb | material sufficiency events | `human_like_reviewer` or `project_manager` per phase |
| `research` | PM research package | worker | `worker.research` | `human_like_reviewer` | reviewer, then PM absorb/mutate | research review/absorb events | `human_like_reviewer` then `project_manager` |
| `control_blocker_repair` | Router control blocker delivered to PM | PM, with optional delegated repair packets | `pm.control_blocker_repair_decision` plus follow-up process binding | Depends on selected follow-up binding | Declared by binding | Declared by selected follow-up binding | Declared by selected follow-up binding |
| `resume_decision` | Router heartbeat/manual resume | PM | `pm.resume_decision` | Router metadata only | PM | `pm_resume_recovery_decision_returned` | `project_manager` |

The implementation should store this logic as a small Router-owned registry or
normalizer rather than as scattered PM-specific conditionals. Existing contract
registry rows can remain the source for contract metadata; the Router binding
layer decides which registry rows are legal for the active process kind.

## Optimization Sequence

| Step | Optimization point | Concrete work | Validation gate |
| --- | --- | --- | --- |
| 1 | Capture the cross-process binding contract | Add/upgrade a FlowGuard model with explicit process kind, initiator, target role, output contract family, result recipient, absorbing role, closure event, and event producer. | Hazards below are detected before production code changes. |
| 2 | Build the safe binding table in the model | Model all common process kinds, not just PM role work. | Safe scenarios for current-node work, PM role-work, officer report, material scan, research, control-blocker repair, and resume pass. |
| 3 | Add source conformance scan | Have the model inspect Router/contract registry facts for process-contract binding coverage. | Current source fails before the production repair if mismatches are present. |
| 4 | Add Router binding validation at packet creation | Before any packet is written, Router validates process kind, contract family, target role, packet type, and required result recipient. | Mismatched packet is rejected before files/state are written. |
| 5 | Add Router binding validation at result return | Router validates completed-by role, result `next_recipient`, and expected absorbing role. No silent recipient normalization for new protocol paths. | Bad result envelopes are rejected; valid PM role-work results return to PM. |
| 6 | Add Router binding validation at wait creation | Every wait event must declare a legal producer role, and `to_role` must match that producer or route to it first. | A PM wait for a reviewer-only event is rejected before persistence. |
| 7 | Keep legacy repair compatibility explicit | Existing delivered blockers may still be recovered through documented legacy fallback, but new packets/waits use strict binding. | Regression tests prove old blocker recovery still works without allowing new mismatches. |
| 8 | Sync local install and local git only | After tests pass, sync the installed local skill from this repository and make a scoped local commit. | Installed skill matches repo; no remote push. |

## Bug/Risk Checklist

| Risk id | Possible bug introduced or exposed | Why it matters | FlowGuard must catch it by |
| --- | --- | --- | --- |
| R1 | A process uses a contract family from another process. | The result may go to the wrong role or close with the wrong event. | Process/contract family invariant. |
| R2 | A valid target role is paired with a contract that does not allow that role. | The role can receive a packet it cannot satisfy. | Target-role/contract-recipient invariant. |
| R3 | A result's `next_recipient` differs from the process-required recipient. | Router may wait for the wrong absorber or silently patch state. | Result-recipient invariant. |
| R4 | Router normalizes a bad recipient instead of rejecting a new bad packet/result. | Compensation hides protocol drift until a later dead end. | No-compensation invariant for new strict paths. |
| R5 | A wait expects a reviewer-only event while `to_role` is PM. | PM cannot legally produce the event, causing a dead wait. | Wait-event producer invariant. |
| R6 | A control-blocker repair chooses a follow-up event without a binding path to its producer. | Repair decision is accepted but cannot actually close. | Repair follow-up binding invariant. |
| R7 | A PM role-work request to a worker incorrectly uses `worker.current_node`. | This is the observed bug class. | Negative scenario for PM role-work/current-node contract mismatch. |
| R8 | Current-node worker packets are accidentally forced to use PM role-work contracts. | Real node execution would stop going through reviewer review. | Safe current-node scenario plus wrong-for-current-node hazard. |
| R9 | Officer model-miss requests are blocked because they are not PM role-work. | PM must still delegate model-miss analysis. | Safe officer-report scenario. |
| R10 | Material scan or research flows lose reviewer-first review. | Evidence quality gates can be bypassed. | Safe material/research reviewer recipient scenarios. |
| R11 | Existing delivered control blockers become unrecoverable. | Active runs need an escape path from old artifacts. | Legacy recovery scenario with explicit compatibility lane. |
| R12 | Source conformance passes while only prose says the binding exists. | Runtime can still drift from docs. | Source scan must check executable Router/contract facts, not only docs. |

## FlowGuard Coverage Contract

| Coverage item | Required model evidence | Required production evidence |
| --- | --- | --- |
| Current bug class is visible | Hazard: PM role-work request selects `worker.current_node`; model rejects it. | Runtime test rejects that request before packet creation. |
| All roles use the same binding rule | Safe/hazard cases cover PM, worker, reviewer, and officer process kinds. | Router helper is generic and table-driven. |
| Result recipient drift is caught | Hazard: result recipient differs from binding-required recipient; model rejects it. | Runtime test rejects bad result envelope instead of normalizing on strict paths. |
| Wait producer mismatch is caught | Hazard: wait for reviewer event with PM as `to_role`; model rejects it. | Runtime test rejects or redirects before waiting. |
| Valid existing flows still pass | Safe scenarios for current-node, PM role-work, officer, material, research, control-blocker, resume. | Existing focused tests still pass. |
| Legacy active runs have a recovery lane | Legacy scenario allows documented fallback only for pre-existing artifacts. | Existing legacy control-blocker tests still pass. |

## Minimal Implementation Boundary

The implementation should avoid a broad Router rewrite. The smallest root fix:

- Add a Router-owned binding registry/helper for process kind to allowed
  contract family, target role class, required result recipient, absorbing role,
  closure events, and legal producers.
- Call the helper in PM role-work packet creation, current-node packet/result
  handling, role-work result return, control-blocker repair follow-up selection,
  and wait-boundary construction.
- Replace silent PM role-work result recipient normalization with strict
  rejection for newly created strict-binding packets. Keep a documented legacy
  fallback only when an older packet lacks the binding marker.
- Add focused runtime tests around the helper instead of duplicating the full
  route loop.

## Non-Goals

- Do not push to GitHub.
- Do not redesign the entire packet runtime.
- Do not read sealed packet/result/report bodies.
- Do not overwrite concurrent unrelated changes.
- Do not remove legacy recovery for already persisted runs unless a separate
  migration proves it is safe.
