# FlowPilot Unified Role Recovery Plan

## Goal

FlowPilot must treat background-role loss as an urgent control-plane recovery
event. Whether the trigger is a heartbeat/manual resume or a mid-run Controller
liveness fault, the Controller should enter the same recovery engine before
normal route work, waits, packets, gates, or blocker handling continue.

The recovery engine should prefer minimal targeted repair, but it must have a
complete escalation ladder when a role cannot be restored or replaced.

## Optimization Checklist

| Step | Optimization point | Concrete change | Done signal |
| --- | --- | --- | --- |
| 1 | Define one recovery engine, not separate heartbeat and mid-run recovery paths. | Add a durable role-recovery transaction schema and route both `heartbeat_or_manual_resume_requested` and a new mid-run role liveness fault event through that transaction. | Recovery records carry `trigger_source`, `scope`, `target_role_keys`, `crew_generation`, and `priority=preempt_normal_work`. |
| 2 | Make recovery priority explicit. | The next-action selector checks pending recovery before normal waits, packet routing, active control blockers, route advancement, and gate actions. | With recovery pending, the next action is a recovery action unless the user explicitly stopped/cancelled or terminal cleanup is already required. |
| 3 | Preserve the existing heartbeat/manual resume behavior through the unified path. | Heartbeat/manual resume still loads current-run state, restores visible plan, refreshes crew memory, and requires PM resume decision, but crew restoration is recorded as a role-recovery transaction. | Existing resume checks still pass and a recovery report is written before PM resume decision. |
| 4 | Add mid-run single-role recovery entry. | Add a Controller/router event for a role that is missing, cancelled, unknown, timed out, or no longer addressable. It records the fault, suspends normal route work, and starts targeted recovery for the affected role. | A mid-run fault for one role produces a targeted recovery action rather than waiting on old work. |
| 5 | Implement the recovery ladder. | For each failed role: try old-agent restore first; if restore fails, spawn a targeted replacement; if capacity/full-slot conflict prevents replacement, reconcile slots; if close/spawn cannot resolve the issue, recycle the full six-role crew; if full recycle fails, block for environment/user action. | The report includes ordered attempts and one terminal result: restored, targeted replacement, full crew recycle, or environment blocked. |
| 6 | Preserve current-run memory and work context. | Recovery actions must inject current-run memory, current node/packet context, and ledger summaries into restored or replacement agents. The report must say exactly what was injected. | No recovered role is marked usable without memory/context injection evidence. |
| 7 | Prevent stale-agent late output from corrupting the route. | Add `crew_generation` and per-role `role_binding_epoch` bookkeeping. Late output from an older generation/epoch is quarantined and cannot complete current packets or gates. | Old-generation output creates a quarantine/control record, not route progress. |
| 8 | Reconcile packet ownership before normal work resumes. | If the lost role held an active packet or pending result obligation, recovery must mark that packet as reconciled: reused result, reassigned packet, or PM decision required. | PM can continue only after the recovery report explains packet/result ownership. |
| 9 | Let PM decide after recovery. | After recovery, Controller does not infer that the old work should continue. PM gets the recovery report and decides whether to resume, re-dispatch, absorb an existing result, or escalate. | The next non-recovery step is a PM recovery/resume decision, not automatic route advancement. |
| 10 | Update Controller/PM prompt cards. | Controller card says any role-loss/recovery signal preempts normal waits and must use the unified recovery engine. PM resume/current-node cards say recovery reports are mandatory input before continuation. | Card instruction coverage can find recovery-first wording in Controller and PM cards. |
| 11 | Keep local install in sync after validation only. | After model checks and runtime tests pass, sync the repo-owned skill into the local installed FlowPilot skill. Do not push remote GitHub. | Local install audit reports no source/install drift. |

## Bug And Regression Risks To Model

| Risk id | Possible bug | Why it matters | FlowGuard coverage required | Runtime coverage required |
| --- | --- | --- | --- | --- |
| R1 | Recovery waits behind normal route work, active blockers, packet waits, or gate waits. | The waited-on work may depend on the missing role and never complete. | Hazard: `normal_work_preempts_recovery`. Invariant: recovery pending must be the next control priority. | Router test: role fault with active blocker still returns recovery action first. |
| R2 | Heartbeat/manual resume bypasses the new recovery engine and uses a separate path. | Two recovery paths diverge and future fixes cover only one. | Hazard: `heartbeat_bypasses_unified_recovery`. Invariant: heartbeat uses a recovery transaction before PM resume. | Resume test: heartbeat writes role-recovery report as part of rehydration. |
| R3 | Mid-run role fault is treated as a normal timeout or waiting condition. | Controller may keep waiting for an agent that no longer exists. | Hazard: `mid_run_fault_treated_as_wait`. Invariant: missing/cancelled/unknown role is recovery-needed. | Router test: mid-run fault records recovery request and returns recovery action. |
| R4 | Targeted recovery skips old-agent restore and immediately replaces live agents. | Live useful context is thrown away and work continuity gets worse. | Hazard: `targeted_replace_before_restore`. Invariant: restore is attempted before replacement unless explicitly impossible. | Recovery payload validation requires ordered attempts. |
| R5 | One failed role triggers full six-role recycle too early. | Unaffected agents lose context unnecessarily. | Hazard: `full_recycle_without_targeted_attempt`. Invariant: full recycle requires failed restore plus failed targeted replacement/slot reconciliation. | Test: one-role failure expects targeted scope first. |
| R6 | Capacity/full-slot conflict deadlocks because old role cannot close and new role cannot spawn. | Controller gets stuck with no usable role and no escalation. | Hazard: `capacity_full_without_full_recycle`. Invariant: close failure plus spawn capacity failure escalates to full crew recycle. | Recovery report validation requires full recycle attempt in this case. |
| R7 | Full crew recycle failure is hidden as success. | System appears resumed while no reliable crew exists. | Hazard: `failed_full_recycle_marked_ready`. Invariant: failed full recycle blocks environment/user action. | Runtime validation rejects ready report without six usable roles. |
| R8 | Recovered/replacement role is marked active without current-run memory injection. | The new role cannot inherit durable progress and may redo or corrupt work. | Hazard: `ready_without_memory_injection`. Invariant: ready roles require memory/context injection. | Report validation requires injected memory/context fields. |
| R9 | Old-generation late output is accepted after replacement. | A stale agent can complete a packet after a new agent owns that role. | Hazard: `stale_generation_output_accepted`. Invariant: old epoch output is quarantined. | Runtime test: old agent result produces quarantine/blocker, not progress. |
| R10 | Packet ownership is not reconciled before PM continues. | Active packet/result obligations may be lost or duplicated. | Hazard: `pm_continue_without_packet_reconciliation`. Invariant: packet-holder loss requires packet reconciliation before PM continuation. | Recovery report validation requires packet ownership disposition. |
| R11 | Controller auto-continues after recovery without PM decision. | Controller becomes a project decision maker instead of relay/control plane. | Hazard: `controller_auto_continues_after_recovery`. Invariant: PM decides after recovery report. | Router test expects PM recovery decision action after recovery. |
| R12 | User stop/cancel cannot interrupt recovery. | Explicit user control must remain highest priority. | Hazard: `recovery_blocks_user_stop`. Invariant: explicit stop/cancel may preempt recovery. | Existing terminal/cancel tests continue to pass. |

## FlowGuard Upgrade Plan

The new model will represent the recovery engine as:

`Trigger x State -> Set(Action x State)`

The state will track:

- trigger source: heartbeat, manual resume, or mid-run liveness fault;
- recovery priority and whether normal work is suspended;
- recovery scope: all-six sweep, targeted role, slot reconciliation, full crew;
- per-role liveness, restore attempt, replacement attempt, memory injection,
  binding generation, and packet ownership;
- PM decision readiness after recovery;
- terminal blocked states for environment failures.

The model must first prove it detects all risks in the table above by running
known-bad hazard states. Only after those hazards are detected can the model
run the target safe plan and prove:

- there is at least one successful targeted-recovery path;
- there is at least one successful heartbeat/manual all-six sweep path;
- there is at least one successful full crew recycle path;
- there is at least one blocked environment path;
- no explored safe state violates the recovery-first, memory-injection,
  generation-quarantine, packet-reconciliation, or PM-decision invariants;
- every non-terminal explored state can reach either success or an explicit
  blocked terminal state.

## Implementation Order

1. Add this written plan.
2. Add the role recovery FlowGuard model and runner.
3. Run hazard checks and confirm every listed risk is detected.
4. Run the safe recovery graph and FlowGuard explorer; fix the model if it
   misses any user-stated recovery rule.
5. Add or update templates/schemas for role recovery reports.
6. Add router event handling for mid-run role liveness faults.
7. Add recovery-first next-action priority.
8. Add recovery report validation and recovery ladder result recording.
9. Add generation/epoch fields and stale-output quarantine checks.
10. Update Controller and PM cards with recovery-first instructions.
11. Run focused tests after each meaningful step.
12. Run relevant FlowGuard suites and local install checks.
13. Sync the validated repo-owned FlowPilot skill to the local installed skill.
14. Commit locally if the repository remains healthy; do not push.

## Verification Plan

| Stage | Command family | Expected result |
| --- | --- | --- |
| FlowGuard availability | import real `flowguard` | Schema version prints successfully. |
| Model syntax | compile new model/runner | No syntax errors. |
| Hazard detection | new role recovery runner | Every listed bad case is detected. |
| Safe-plan proof | new role recovery runner | Safe graph, progress check, and FlowGuard explorer pass. |
| Router regression | targeted pytest tests | Recovery preempts normal work and heartbeat still resumes. |
| Existing related suites | resume, router, role output, packet runtime tests | No regressions in current behavior. |
| Broad FlowPilot model checks | meta/capability checks when touched | No control-flow or capability regressions. |
| Local install sync | install sync and audit scripts | Local installed skill matches validated repo source. |

