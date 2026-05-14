# FlowPilot Wait Reconciliation Optimization Plan

## Risk Intent Brief

This change uses FlowGuard because it changes FlowPilot control flow, durable
packet state, waits, idempotency, event authority, and PM/reviewer gate timing.
The protected harm is a Router that either waits unnecessarily after evidence
already exists, or moves too early past a gate that still depends on missing
packet results.

FlowGuard must be upgraded before production code changes. The model suite must
first fail known-bad traces, then pass the intended design, before Router,
packet-runtime, template, or prompt-card edits begin.

## Optimization Sequence

| Step | Optimization | Concrete Change | Main Files | Verification Gate |
| --- | --- | --- | --- | --- |
| 1 | Durable wait reconciliation | Before emitting a wait action, scan packet ledger, ACK files, result envelopes, and controller status packets; consume valid already-returned evidence and refresh run state. | `skills/flowpilot/assets/flowpilot_router.py`, `templates/flowpilot/packet_ledger.template.json`, `templates/flowpilot/packets/controller_status_packet.template.json` | FlowGuard stale-wait hazards fail before fix and pass after model update; router tests prove returned evidence is consumed before stale wait. |
| 2 | Per-packet partial batch accounting | Track every packet in a batch with status, holder, returned timestamp, result envelope path, dependency class, and missing-role summary. | `flowpilot_router.py`, packet/result templates, `docs/schema.md` | Batch model rejects full-batch unknown state when one result returned; tests show A returned/B missing status. |
| 3 | Accurate user-facing status | Build status summary from active batch members, not only the last active packet or old expected role. Keep it metadata-only. | `flowpilot_router.py`, display/status summary writers | Tests verify status says the real remaining role and never includes sealed body text, findings, or recommendations. |
| 4 | Active-holder fast lane expansion | Issue active-holder leases for material scan, research, and PM role-work packets when a live holder is known; keep fallback behavior for no live agent. | `flowpilot_router.py`, `packet_runtime.py`, worker/officer cards | Router-loop model and runtime tests prove direct ACK/progress/result works outside current-node packets without authority drift. |
| 5 | Dependency-aware ready queue | Classify pending work as `blocking`, `advisory`, or `prep-only`; allow non-dependent actions while pending packets remain unresolved, but block protected gates. | `flowpilot_router.py`, action policy/transaction registries, protocol docs | Decision-liveness model rejects unsafe gate crossing and terminal closure with unresolved advisory work. |
| 6 | Prompt/card contract hardening | Update PM and role cards so packet requests declare dependency class, join policy, allowed events, and active-holder return path. | runtime cards under `skills/flowpilot/assets/runtime_kit/cards/` | Card coverage and event-contract checks reject invented events or prompts that advertise unsupported continuation. |
| 7 | Local install and local git sync | Sync repo-owned FlowPilot assets into the local installed skill, run install checks, then stage/commit local changes only. | `scripts/install_flowpilot.py`, local git | `scripts/check_install.py`, targeted tests, and local git status clean after commit. |

## Bug And Risk Checklist

| ID | Possible Bug | What Would Go Wrong | Required FlowGuard Coverage |
| --- | --- | --- | --- |
| R1 | Stale wait after result exists | Router keeps waiting for worker A even though A already returned. | Control-plane friction model must include an already-existing result envelope plus stale expected-role wait, and fail unless reconciliation happens first. |
| R2 | Partial batch treated as zero returned | One result is invisible, so status and routing stay wrong. | Parallel batch model must track per-packet returned count and fail if batch state says zero after a valid member returned. |
| R3 | Unsafe partial advancement | Router advances PM/reviewer/material sufficiency gate before all blocking members return. | Parallel batch and decision-liveness models must fail any protected gate crossing with unresolved blocking dependency. |
| R4 | Advisory work blocks everything | Non-dependent work freezes while advisory support is pending. | Decision-liveness model must allow non-dependent continuation with advisory pending. |
| R5 | Advisory work lost before closure | Terminal completion happens while advisory result is unresolved, uncanceled, or unsuperseded. | Decision-liveness model must fail terminal closure with unresolved advisory work. |
| R6 | Ready queue does work that actually depends on missing result | Router misclassifies dependent PM/reviewer work as ready. | Dependency-aware model must carry `blocks_gate_ids` and fail actions whose required gate has pending blockers. |
| R7 | Active-holder authority drift | A role submits ACK/result for a packet it does not hold, or for a stale run. | Router-loop model must check holder, run id, packet id, hash, and current frontier before accepting direct returns. |
| R8 | Invented or stale external event accepted | Role uses an event not currently authorized by Router. | Event-contract and prompt-coverage models must fail unlisted events and legacy direct events outside `allowed_external_events`. |
| R9 | Controller leaks sealed content in status | Status summary contains packet findings, evidence, or body summaries. | Control-plane friction model must fail status summaries that are not metadata-only. |
| R10 | Duplicate reconciliation side effect | Re-running Router consumes the same ACK/result twice or increments counts twice. | Models and tests must include repeated ticks/events and prove idempotent packet-id keyed updates. |
| R11 | Wrong result matched to wrong request | PM role-work result attaches to a different request or wrong role. | Decision-liveness model must require request id, target role, contract id, and ledger check before PM absorption. |
| R12 | Prompt/runtime drift | Cards promise partial continuation or active-holder return paths that runtime does not support. | Card coverage and model-mesh checks must fail prompt/runtime capability mismatches. |

## FlowGuard Upgrade Order

| Order | Model | Required New Scenarios |
| --- | --- | --- |
| 1 | `simulations/flowpilot_control_plane_friction_model.py` | stale wait reconciled from durable packet evidence; metadata-only status for active partial batch; duplicate reconciliation idempotency. |
| 2 | `simulations/flowpilot_parallel_packet_batch_model.py` | member-level returned counts; partial result not zero; protected gates blocked until all blocking members return; nonblocking status/relay allowed. |
| 3 | `simulations/flowpilot_decision_liveness_model.py` | advisory pending allows non-dependent work; advisory blocks terminal closure; blocking dependency blocks dependent PM final decision only. |
| 4 | `simulations/flowpilot_router_loop_model.py` | active-holder leases for material/research/role-work packets; stale holder or wrong packet direct return rejected. |
| 5 | `simulations/flowpilot_event_contract_model.py` and `simulations/flowpilot_event_capability_registry_model.py` | dynamic `allowed_external_events` authority for partial batch and role-work returns. |
| 6 | `simulations/flowpilot_model_mesh_model.py` | mesh treats all upgraded child models as current evidence before production confidence. |

## Required Pre-Implementation Proof

Before production runtime edits:

1. Add model-level known-bad states for each risk above.
2. Run the relevant model checks and confirm known-bad states fail.
3. Update the modeled intended design.
4. Run the model checks again and confirm intended states pass.
5. Record the model evidence path and any skipped boundary.

## Production Implementation Rules

- Do not infer progress from chat text.
- Do not read sealed packet or result bodies in Controller code.
- Do not advance PM/reviewer/material sufficiency gates on partial blocking input.
- Do not let advisory requests vanish; absorb, cancel, supersede, or explicitly carry them before terminal closure.
- Do not overwrite other agents' unrelated changes. Inspect `git status` before each implementation slice and work only on the slice files.
- Run targeted tests after each slice, then broader install and model checks at the end.
- Sync only local install, local repository, and local git. Do not push or create a remote GitHub release/PR.
