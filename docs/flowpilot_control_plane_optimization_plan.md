# FlowPilot Control-Plane Optimization Plan

Date: 2026-05-11

## Scope

This plan optimizes FlowPilot speed by reducing mechanical controller turns.
It must not weaken sealed-body boundaries, PM authority, reviewer gates, role
identity checks, hash checks, or packet-runtime receipt checks.

## Optimization Checklist

| Order | Optimization | Current behavior | Target behavior | Primary code location | Guardrail |
| --- | --- | --- | --- | --- | --- |
| 1 | Human-readable status summary | Users and Cockpit must infer current state from large ledgers and route/frontier files. | Router writes a compact current-status summary after state changes. Chat shows it with Mermaid only when Cockpit is unavailable; Cockpit can read the same JSON. | `flowpilot_router.py`, Cockpit adapter later | Summary is derived only from public state/envelopes, never sealed bodies. |
| 2 | Stop cleanup reconciliation | Stop can close heartbeat and agents while `.flowpilot/current.json` or index still say running/controller-ready. | User stop/cancel updates current pointer, run index, continuation binding, frontier, crew status, and a stop receipt together. | `flowpilot_router.py`, possibly `scripts/flowpilot_lifecycle.py` | Stop is lifecycle state only; it does not claim route completion. |
| 3 | Pending wait reconciliation | Router can keep waiting for a role even after packet ledger/status packet shows the result is ready. | Router clears stale `await_role_decision` waits when durable packet evidence proves the awaited result already exists and is ready for the next relay. | `flowpilot_router.py` | Reconciliation requires packet ledger/status packet plus role/hash validation; no chat inference. |
| 4 | Card ack auto-consumption | Controller often has to run a separate `check_card_return_event` after an ack already exists. | Router consumes valid card/bundle acks internally before choosing the next external wait. | `flowpilot_router.py` | Validation uses the same card runtime checks; invalid or incomplete acks still stop. |
| 5 | Role-work recipient normalization | Role-work result content can be valid but rejected because `next_recipient` points to reviewer instead of PM. | Runtime/router treats PM role-work results as PM-returning by default and blocks only substantive or unsafe mismatches. | `packet_runtime.py`, `flowpilot_router.py`, contracts/card text | Current-node worker results still go to reviewer; only PM role-work results default to PM. |
| 6 | Model-miss report completeness | PM can need a second officer request because the first model-miss report lacks self-check or PM decision fields. | Model-miss/officer request contracts require a small complete decision-support matrix on first return. | `runtime_kit` cards/contracts, `role_output_runtime.py` if needed | Adds fixed fields, not a new review loop. |
| 7 | Role memory delta | Six role memory files can remain empty after real work, forcing resume to read large ledgers. | Runtime writes a tiny role-memory delta after every accepted role output or packet result. | `role_output_runtime.py`, `packet_runtime.py`, `flowpilot_router.py` | Memory is an index only; it cannot approve gates or replace ledgers. |
| 8 | UI status integration | Cockpit route map can show route state but not the same compact status summary. | Cockpit displays `status/current_status_summary.json`; chat uses it when Cockpit is absent. | Cockpit implementation later | No evidence/source/hash table appears in the main UI. |

## Bug/Risk Checklist for FlowGuard

| Risk id | Possible bad optimization | Required FlowGuard detection |
| --- | --- | --- |
| R1 | Auto-consuming a card ack without validating the exact card, role, receipt, or hash. | Fails if an optimized ack transaction lacks ack validation, role check, or hash check. |
| R2 | Clearing a pending role wait from stale chat/history instead of packet ledger/status packet evidence. | Fails if pending reconciliation lacks durable packet evidence and hash/role checks. |
| R3 | Status summary exposes sealed body content, evidence tables, hashes, or source fields in user-facing text. | Fails if user-visible summary is not metadata-only. |
| R4 | Stop cleanup marks the run complete or leaves heartbeat/crew/packet/frontier authority active. | Fails if stopped state still has active authorities or claims completion. |
| R5 | PM role-work recipient normalization accidentally reroutes normal current-node worker results away from reviewer. | Fails if current-node result no longer routes to reviewer or PM role-work no longer routes to PM. |
| R6 | Role memory becomes an authority source for approvals or replaces packet/reviewer evidence. | Fails if resume/completion can use role memory as approval evidence. |
| R7 | Model-miss report completeness adds a second mandatory loop instead of replacing a second loop. | Fails if model-miss cannot reach PM decision from one complete officer report. |
| R8 | Compact status or optimized transaction hides unresolved blockers. | Fails if summary says no blocker while control blocker or pending repair exists. |

## Execution Rules

1. Upgrade and run the FlowGuard control-plane friction model before production edits.
2. Each optimization must have at least one known-bad hazard state.
3. Known-bad hazard states must fail for the intended reason.
4. The safe optimized plan must still pass the FlowGuard explorer.
5. After each code slice, run focused unit/smoke checks before continuing.
6. Preserve unrelated existing changes in the shared worktree.
7. Sync only the local repository and local installed skill. Do not push to GitHub.
