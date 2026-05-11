# Direct Router ACK Migration Plan

## Goal

Move all FlowPilot ACK traffic to Router-owned direct check-in paths and remove
the old Controller-mediated or external-event compatibility path.

The target behavior is single-track:

1. System-card ACKs are submitted directly to Router by the addressed role.
2. Current packet ACKs are submitted directly to Router by the active holder.
3. Current packet completion reports are submitted directly to Router by the
   active holder.
4. Router validates mechanics, writes controller-visible next-action notices,
   and decides the next stage.
5. Controller waits for Router status/notice and relays formal cross-role mail
   only when Router instructs it to do so.

## Implementation Checklist

| Step | Change | Primary files | Done signal |
| --- | --- | --- | --- |
| 1 | Record this plan and the risk ledger before production edits. | `docs/direct_router_ack_migration_plan.md` | Plan lists affected areas, old paths to remove, and model/test coverage. |
| 2 | Upgrade the card ACK FlowGuard model for direct Router ACKs and prompt coverage. | `simulations/flowpilot_card_envelope_model.py`, `simulations/run_flowpilot_card_envelope_checks.py` | Model rejects legacy ACK paths and missing/new-stale prompt guidance hazards. |
| 3 | Run the upgraded model before runtime edits. | `simulations/flowpilot_card_envelope_results.json` | Model passes and hazard table proves all listed risks are detected. |
| 4 | Make system-card ACKs token/direct-router only. | `skills/flowpilot/assets/card_runtime.py`, `skills/flowpilot/assets/flowpilot_runtime.py`, `skills/flowpilot/assets/flowpilot_router.py` | Valid runtime ACKs carry direct Router authorization; stale or tokenless ACKs fail. |
| 5 | Remove legacy card ACK compatibility. | `skills/flowpilot/assets/flowpilot_router.py` | `record_external_event(..., "*_card_ack")` no longer reroutes; it raises a protocol error. |
| 6 | Keep packet ACK/result fast lane as the packet-local Router path and align text around it. | `skills/flowpilot/assets/packet_runtime.py`, `templates/flowpilot/packets/*.template.md` | Packet bodies tell active holders to ACK and return packet completion to Router, not Controller. |
| 7 | Update all role/system/phase/reviewer/officer cards that still teach old ACK routing. | `skills/flowpilot/assets/runtime_kit/cards/**/*.md` | No card prompt says Controller should receive, teach, hand-write, or relay ACKs. |
| 8 | Update protocol documentation and skill guidance. | `skills/flowpilot/SKILL.md`, `skills/flowpilot/references/*.md`, `docs/*.md` | Docs describe ACKs as Router-direct and formal mail as Controller-relayed by Router instruction. |
| 9 | Update tests for new pass/fail behavior. | `tests/test_flowpilot_card_runtime.py`, `tests/test_flowpilot_router_runtime.py`, `tests/test_flowpilot_packet_runtime.py` | New path passes; old compatibility path fails. |
| 10 | Sync local install and local git only. | installed skill under user Codex home, local repository | Install audit passes; local commit exists; no GitHub push. |

## Affected Surface

| Surface | Current risk | Required result |
| --- | --- | --- |
| Router card return event handling | Old external-event ACKs can still be auto-rerouted. | Old external-event ACKs are rejected as legacy protocol violations. |
| Card runtime ACK envelopes | ACKs prove receipt but do not yet make the Router-direct authorization explicit enough. | ACK envelopes include direct Router authorization fields tied to run, role, agent, delivery, card hash, and expected return. |
| Controller card | Controller guidance still mentions role/event envelopes and ACK handling in a way that can preserve old habits. | Controller is told to wait for Router card/packet status and never receive, write, or relay ACKs. |
| Role cards | Many role cards still say role outputs return to Controller, which is correct for formal reports but ambiguous for ACKs. | Cards distinguish mechanical ACKs from formal mail: ACKs go to Router; reports/decisions follow Router-directed formal mail. |
| Packet body template | It still says return a result envelope to Controller. | Current active holder first ACKs Router and returns packet completion to Router; Controller receives only Router next-action notice. |
| Result body template | It still describes formal result return through the old packet path. | It distinguishes active-holder direct Router submission from later Controller relay to the next recipient. |
| Protocol docs | Some docs say all formal mail goes through Controller without carving out mechanical ACKs. | Docs say ACKs/check-ins are Router-direct; formal cross-role envelopes remain Controller-relayed. |
| Prompt/card coverage tests | Old text can remain unnoticed. | Tests fail when old ACK instructions remain or new Router-direct instructions are missing. |

## Risk Ledger

| Risk id | Failure mode | Model/test must catch |
| --- | --- | --- |
| R1 | A card ACK is accepted as a normal external event. | FlowGuard hazard and router runtime test reject external-event card ACK. |
| R2 | Router silently reroutes old card ACK compatibility instead of rejecting it. | FlowGuard hazard and router runtime test require hard failure. |
| R3 | Controller hand-writes, receives, or relays a system-card ACK. | Prompt coverage test and FlowGuard prompt hazard fail. |
| R4 | A role card or packet still instructs ACK return to Controller. | Prompt coverage scan fails on stale ACK/Controller phrases. |
| R5 | New Router-direct ACK instruction is missing from a role/system card that needs it. | Prompt coverage scan fails for missing direct Router ACK wording. |
| R6 | New active-holder packet ACK/result guidance is missing from work packets. | Packet template/runtime test fails for missing active-holder Router guidance. |
| R7 | Wrong role, wrong agent, old run, old delivery, stale hash, or stale route/frontier ACK is accepted. | FlowGuard identity hazards and card runtime tests fail. |
| R8 | Duplicate ACK advances state twice. | Runtime idempotency test and model duplicate-side-effect invariant fail. |
| R9 | Same-role bundle ACK advances with missing per-card receipts. | Existing bundle FlowGuard hazard and card runtime test fail. |
| R10 | Mechanical system-card ACK is treated as semantic review/PM approval. | Existing FlowGuard semantic-gate invariant remains required. |
| R11 | Controller does not know when to move after direct Router submission. | Router writes next-action/status notice; router/packet tests verify it. |
| R12 | Documentation keeps teaching dual-track behavior. | Documentation/prompt scan fails on legacy ACK routing terms. |

## Verification Plan

Run these in order:

1. `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
2. `python simulations/run_flowpilot_card_envelope_checks.py --json-out simulations/flowpilot_card_envelope_results.json`
3. Focused card runtime tests.
4. Focused router runtime tests around card ACK check-in and rejected legacy external-event ACK.
5. Focused packet runtime tests around active-holder ACK/result guidance.
6. Prompt coverage scan for stale ACK instructions and missing Router-direct instructions.
7. `python simulations/run_meta_checks.py`
8. `python simulations/run_capability_checks.py`
9. `python scripts/check_install.py`
10. `python scripts/install_flowpilot.py --sync-repo-owned --json`
11. `python scripts/audit_local_install_sync.py --json`
12. `python scripts/install_flowpilot.py --check --json`

Long-running model and broad validation commands should be launched in a way
that preserves logs and lets other work continue, then their results must be
read before claiming completion.

## Non-goals

- Do not push to GitHub.
- Do not add a permanent old-ACK compatibility bridge.
- Do not change semantic PM/reviewer/officer decision authority.
- Do not make Controller read sealed packet or result bodies.
