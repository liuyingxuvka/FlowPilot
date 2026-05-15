## Context

Current FlowPilot already contains substantial script implementation. Startup
deterministic setup is now handled by a deterministic bootstrap seed, and many
Controller action types have Python handlers in `apply_controller_action`.

The remaining problem is ownership, not missing primitives. If an action is
pure Router bookkeeping, the Router should consume it internally and should not
write a Controller row just so the Controller can call back into the Router. If
an action represents host authority, role interaction, or prompt/work-package
delivery, it must remain a Controller work package.

## Goals / Non-Goals

**Goals:**

- Make local Router bookkeeping a Router-internal path, not Controller work.
- Preserve Controller authority for heartbeat, role recovery/rehydration,
  system-card relay, formal packet/result handoff, and prompt boundary work.
- Add explicit optimization and risk inventories before code edits.
- Add FlowGuard coverage that proves known-bad variants are caught before the
  production runtime changes are trusted.
- Keep changes narrow and compatible with parallel agent work.

**Non-Goals:**

- Do not automate host tools from local Python.
- Do not remove the Controller action ledger.
- Do not let PM, Worker, Reviewer, or officer roles communicate outside the
  Controller-controlled channel.
- Do not read sealed packet, result, report, or user-intake bodies in Router or
  Controller bookkeeping paths.
- Do not run heavyweight Meta or Capability simulations in this task.

## Optimization Inventory

| Order | Optimization point | Current behavior | Target owner | Target behavior | Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | Classify action ownership | Action type implies behavior indirectly through scattered checks | Router classifier | Each action is classified as `router_internal`, `controller_work_package`, or boundary/semantic work before queueing | Unit tests for representative actions |
| 2 | Internal ledger/manifest checks | Local checks can appear as Controller rows | Router | `check_prompt_manifest` and `check_packet_ledger` are consumed by Router when no user/host/role boundary is crossed | FlowGuard leak hazard + focused router test |
| 3 | Internal durable wait reconciliation | Router already reconciles durable evidence, but wait/check rows can still surface | Router | ACK/check/wait bookkeeping is resolved from ledgers before a Controller row is written; missing evidence remains a Router wait/blocker, not Controller busywork | Replay/idempotency tests |
| 4 | Internal local proof writers | `write_startup_mechanical_audit` is script implemented but Controller-visible | Router | Router writes local mechanical proofs itself once prerequisites are met | Test audit/proof exists and no Controller row for pure local audit |
| 5 | Internal display projection generation | `sync_display_plan` mixes local projection with user-dialog display confirmation | Split owner | Router updates local display files/snapshots internally; actual user-dialog display confirmation remains Controller/user boundary | Test local projection can update without claiming dialog display |
| 6 | Controller work packages remain external | System-card and work-packet paths are partly auto-committed but still role-facing | Controller | System-card relay, formal work packet relay, heartbeat, role spawn/recovery remain Controller work packages | FlowGuard swallow hazard + existing ACK/packet tests |
| 7 | Failure and idempotency | Repeated ticks or failures can create duplicate rows/blockers if ownership is unclear | Router reconciler | Router-internal success/failure is idempotent; failures do not become done receipts | Repeated tick tests and hazard checks |
| 8 | Install sync | Repo and installed skill can diverge | Install scripts | Sync after focused tests pass | `install_flowpilot.py --sync-repo-owned --json` and check/audit |

## Risk Catalog

| Risk ID | Possible bug | Why it matters | FlowGuard coverage |
| --- | --- | --- | --- |
| R1 | Router-internal action still creates a Controller row | Keeps the false-blocker/button-pusher class alive | `router_internal_leaked_to_controller_row` |
| R2 | Controller work package is swallowed internally | Controller loses authority over roles/host/system cards | `controller_work_package_swallowed_by_router` |
| R3 | Router internally consumes a role-facing relay | PM/Worker/Reviewer communication can bypass Controller | `role_interaction_bypassed_controller` |
| R4 | Router reads sealed bodies while doing local work | Violates prompt/body isolation | `sealed_body_read_during_internal_work` |
| R5 | Missing ACK/result is marked as success | Work can advance before a role actually responded | `missing_external_evidence_marked_done` |
| R6 | Repeated daemon ticks repeat local side effects | Duplicate ledger rows, duplicate proof writes, or repeated blocker creation | `router_internal_repeated_side_effect` |
| R7 | Local display projection is treated as user display confirmation | User-facing evidence is forged by local file generation | `display_projection_claimed_as_user_confirmation` |
| R8 | Host-boundary action is treated as local script work | Heartbeat/agent recovery can be falsely recorded | `host_boundary_consumed_locally` |
| R9 | Router failure becomes a done receipt | Bad local state hides behind successful reconciliation | `router_internal_failure_marked_done` |
| R10 | Parallel agent work is overwritten | Other accepted changes are lost | Covered by workflow discipline and git status checks, not model semantics |

## FlowGuard Coverage Matrix

| Planned change | Modeled state/events | Known-bad hazards that must fail | Safe path that must pass |
| --- | --- | --- | --- |
| Add ownership classifier | `action_kind`, `classified`, `controller_row_written`, `router_event_written` | R1, R2, R8 | Router-internal classified before queueing; Controller work package preserved |
| Internal checks | `local_check_needed`, `local_check_applied`, `controller_row_written` | R1, R6, R9 | Local check writes one Router event and no Controller row |
| Internal wait reconciliation | `ack_expected`, `ack_present`, `waiting_recorded`, `done_recorded` | R5, R6 | Missing ACK records wait; present ACK advances once |
| Local proof writers | `mechanical_proof_needed`, `proof_written`, `controller_row_written` | R1, R6, R9 | Proof written once after prerequisites |
| Display projection split | `projection_needed`, `projection_written`, `user_display_confirmed` | R7 | Projection is local; user confirmation remains separate |
| Preserve Controller work packages | `role_interaction`, `host_boundary`, `system_card_delivery`, `packet_relay` | R2, R3, R8 | Controller row is written and Router does not self-complete |

## Decisions

1. Router-internal work does not go through a `Controller Runtime`.
   - Rationale: if Router owns the state and proof, adding a Controller-shaped
     runtime preserves the extra ownership surface.
   - Alternative rejected: make Controller Runtime auto-apply local work. That
     still creates Controller rows for Router bookkeeping.

2. Controller work packages remain visible.
   - Rationale: Controller is the main AI authority for host/role interaction,
     system-card relay, work-package relay, prompt visibility, and live crew
     recovery.
   - Alternative rejected: Router self-relays all packets/cards. That would
     weaken role-communication authority.

3. Split local display projection from user-dialog confirmation.
   - Rationale: local files can be generated by Router, but only host/user
     evidence can prove that the user saw the display.
   - Alternative rejected: treat file generation as display confirmation.

4. Use focused FlowGuard first.
   - Rationale: this is a stateful ownership change with idempotency and
     authority risks.
   - Alternative rejected: patch production first and rely only on runtime
     tests.

## Risks / Trade-offs

- Existing tests may expect local checks as Controller rows -> update tests to
  assert Router events/proofs instead.
- Some actions combine local and external responsibilities -> split only the
  local part; leave the external part as Controller work.
- A broad classifier can accidentally move too much -> start with a conservative
  allowlist and expand only when tests/model evidence support it.
- Meta/Capability models are skipped by user direction -> record the residual
  risk and rely on focused model/test boundaries for this change.

## Migration Plan

1. Add the focused FlowGuard model and runner for Router-internal mechanical
   ownership.
2. Prove every known-bad hazard is detected and the safe plan passes.
3. Implement an explicit Router-internal action allowlist/classifier.
4. Move the first safe local actions off Controller rows.
5. Add tests for no Controller row, idempotent Router event/proof, and preserved
   Controller rows for role/host work packages.
6. Repeat in slices for wait reconciliation, local proof writers, and local
   display projection.
7. Run focused model/tests after each slice.
8. Sync installed FlowPilot skill and verify local git state.

## Open Questions

- Which local actions should be in the first implementation slice if a test
  exposes high coupling? Default: start with `check_prompt_manifest`,
  `check_packet_ledger`, and `write_startup_mechanical_audit`.
- Whether packet/result relay should remain entirely Controller work package or
  later split into Router preparation plus Controller delivery. Default for this
  change: keep role-facing relay as Controller work package.
