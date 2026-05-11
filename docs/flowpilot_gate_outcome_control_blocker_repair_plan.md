# FlowPilot Gate Outcome and Control Blocker Repair Plan

Date: 2026-05-11

## Risk Intent Brief

This repair protects the FlowPilot control plane from stale gate outcomes,
wrong-role repair follow-ups, and no-legal-next control blockers created while
a valid role output or gate outcome is still available. The modeled boundary is
the child-skill gate reviewer block/pass loop, card ACK consumption, PM control
blocker repair decisions, and router wait-state reconciliation.

The protected harms are:

- a prior reviewer block remains active after a newer reviewer pass;
- an ACK consumes the visible card wait and loses the semantic reviewer
  pass/block wait;
- PM repair authority is confused with reviewer event authority;
- a duplicate repair decision or stale state creates another blocker instead of
  converging;
- the source repository and installed local skill diverge after the repair.

## Planned Optimization Order

| Step | Optimization point | Concrete change | Required proof before next step |
| --- | --- | --- | --- |
| 1 | Model the bug class first | Extend the control-plane friction model with explicit fields for gate outcome block activity, reviewer pass state, ACK-to-semantic wait preservation, follow-up event authority, pending role output, and duplicate repair decisions. | Hazard states fail for every listed bug class, while the happy path still passes. |
| 2 | Gate outcome lifecycle | Make active gate outcome blockers scoped to the same gate/review generation and clear the active block when a valid newer pass is recorded. | Unit test proves block -> PM rewrite -> reviewer pass leaves no active gate blocker and manifest approval is synced. |
| 3 | ACK to semantic wait continuity | Ensure direct Router card ACK consumption resolves only the mechanical ACK wait and then exposes the next semantic pass/block wait if that card requires one. | Unit test proves after reviewer card ACK the router waits for `reviewer_passes_child_skill_gate_manifest` or `reviewer_blocks_child_skill_gate_manifest`, not `allowed: none`. |
| 4 | Role authority separation | Ensure a control blocker delivered to PM can allow a reviewer follow-up event without letting PM produce that reviewer event. | Unit test proves a PM-origin reviewer-pass envelope is rejected with a role mismatch. |
| 5 | No-legal-next guard | Reconcile stale gate outcome blocks and currently receivable role outputs before emitting a no-legal-next control blocker. | Unit test or live audit proves stale block + available reviewer pass does not create another control blocker. |
| 6 | Idempotent repair decision | Keep repeated PM repair decisions for the same blocker as recorded/idempotent unless the blocker and follow-up context truly changed. | Regression test proves a duplicate PM repair decision does not create a new blocker. |
| 7 | Local installation sync | Copy the repaired source skill into the installed local Codex skill and verify local install freshness without remote GitHub push. | Local install check or file hash comparison proves installed router matches the source router. |

## Possible Bugs This Optimization Could Cause

| Risk id | Possible bug | Why it matters | FlowGuard coverage requirement |
| --- | --- | --- | --- |
| R1 | Clearing the wrong active block | A pass for one gate could accidentally clear a different gate's blocker. | Model must track gate key and generation before allowing clear. |
| R2 | Keeping stale block after valid pass | User sees the same old blocker even though reviewer already passed a newer artifact. | Model must fail if active gate block remains after same-gate current-generation pass. |
| R3 | ACK removes the real reviewer wait | Direct Router ACK works mechanically but the router no longer accepts reviewer pass/block. | Model must fail if card ACK is consumed and semantic wait is absent. |
| R4 | PM impersonates reviewer follow-up | Control blocker repair points to a reviewer event, but PM is accepted as event producer. | Model must fail if reviewer event authority comes from PM target role instead of event role. |
| R5 | No-legal-next blocker created too early | Router emits another control blocker while a valid pending role output or gate event is receivable. | Model must fail if no-legal-next blocker materializes with pending valid role output. |
| R6 | Duplicate repair decision creates blocker churn | A repeated recorded repair decision creates new blocker ids instead of deduping. | Model must fail if duplicate same-blocker PM repair creates a new active blocker. |
| R7 | Repair transaction remains stale after success | The flow advances but the repair lane remains active and later blocks progress. | Existing stale repair invariant must remain green after new fields are added. |
| R8 | Local installed FlowPilot differs from source | The repo passes tests but the Codex-installed skill still has the old router. | Final verification must compare or check installed local skill freshness. |

## FlowGuard Coverage Matrix

| Coverage item | Catches risks | Model mechanism | Expected hazard label |
| --- | --- | --- | --- |
| Active block cleared by same-gate pass | R1, R2 | `gate_outcome_block_active`, `gate_outcome_block_gate_key`, `gate_outcome_pass_recorded`, `gate_outcome_pass_gate_key`, `gate_outcome_same_generation` | `gate_pass_left_active_block` |
| ACK preserves semantic gate wait | R3 | `card_ack_consumed`, `semantic_gate_wait_exposed_after_ack`, `gate_card_requires_semantic_outcome` | `ack_consumed_semantic_wait_lost` |
| Follow-up event role authority | R4 | `control_blocker_target_role`, `followup_event_expected_role`, `followup_event_from_role` | `pm_impersonates_reviewer_followup` |
| No-legal-next waits for valid role output | R5 | `valid_role_output_waiting`, `no_legal_next_control_blocker_materialized` | `no_legal_next_with_valid_role_output` |
| Duplicate PM repair is idempotent | R6 | `pm_repair_decision_recorded`, `duplicate_pm_repair_decision_seen`, `duplicate_repair_created_new_blocker` | `duplicate_pm_repair_created_new_blocker` |
| Existing repair lane cleanup | R7 | Existing `active_repair_transaction_stale` and `repair_recheck_pending_action_stale` invariants | `repair_transaction_stale_after_success` |
| Source/install sync | R8 | Not modeled as router behavior; verified by install audit or hash comparison | Runtime verification only |

## Model Pass Criteria Before Production Code

FlowGuard must show all of the following before production router changes start:

- the new hazard labels above are present in the model check runner;
- each hazard label fails for the intended invariant message;
- the safe graph has no invariant failures, stuck states, or missing required labels;
- the happy path includes a block, PM rewrite, ACK, same-role reviewer pass, and no stale active gate block;
- any skipped conformance or live replay is explicitly recorded as model-level confidence only.

