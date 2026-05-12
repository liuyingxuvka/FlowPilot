# FlowPilot Control Table and Prompt Registry Migration Plan

## Scope

This plan upgrades FlowPilot so role prompts, Router waits, repair outcomes,
and Controller-visible commands are derived from shared control tables instead
of being repeated by hand across cards, work packages, and Router branches.

The first implementation slice is the event-capability registry because it is
the highest-risk control point: an event can be registered in `EXTERNAL_EVENTS`
and still be illegal for the current node kind, repair origin, producer role, or
repair outcome row.

## Optimization Sequence

| Step | Optimization point | Concrete work | FlowGuard gate | Runtime gate |
| --- | --- | --- | --- | --- |
| O1 | Freeze the migration inventory | Inventory prompt/command surfaces: `runtime_kit/manifest.json`, card markdown, `contract_index.json`, `packet_runtime.py` command lists, `EXTERNAL_EVENTS`, repair outcome tables, and Controller action payloads. | Planning table maps each surface to a model or source check. | `scripts/check_install.py` knows the new model/doc artifacts. |
| O2 | Add a first-class event capability registry | Define event capability rows with event name, producer role, node-kind compatibility, repair-origin compatibility, waitability, rerun-target eligibility, and repair outcome eligibility. | New event-capability FlowGuard model catches all listed event/table hazards. | Router uses one validator before writing waits or repair outcome tables. |
| O3 | Split repair outcomes into real exits | Require repair `success`, `blocker`, and `protocol_blocker` rows to have distinct registered, context-compatible events unless a row is explicitly unsupported and rejected before persistence. | Existing repair-transaction and new event-capability models reject collapsed outcome rows. | Material repair keeps three routable events; unsupported generic collapsed outcomes fail before state write. |
| O4 | Lock parent/backward replay repair to parent-safe events | Parent/module backward-replay repairs may only rerun or wait for parent-safe events: parent target build, reviewer backward replay, parent segment decision, parent completion, or a parent protocol blocker. | Event-capability model rejects parent repair targeting leaf current-node packet registration. | Router rejects incompatible `rerun_target` and never persists that wait. |
| O5 | Unify prompt authorization slices | Generate or compose role prompt authorization text from registry rows rather than duplicating command lists in phase cards. | Card/source coverage model must detect manual command text that is not backed by a registry row. | Prompt/card tests compare generated slices with card references. |
| O6 | Cross-check command permission tables | Align `packet_runtime.py` allowed/forbidden actions, Controller action payloads, role output contracts, and event capability rows. | Command-refinement, event-contract, and router-action models cover command/event/recipient drift. | Source checks reject orphan command rows and card commands that have no runtime authority. |
| O7 | Install and local sync harden | Add new model/doc artifacts to install checks and install freshness audit. | Coverage sweep includes the new model in the strong tier. | Local install check passes after sync. |
| O8 | Commit local only | Stage verified repo and installed-local sync changes for local git; do not push remote GitHub. | Adoption log records model-first proof and skipped/long checks. | `git status` shows only intended tracked/untracked residue after commit. |

## Bug and Regression Checklist

| Risk id | Possible bug | Why it matters | Required catch |
| --- | --- | --- | --- |
| B1 | A prompt/card still contains a hand-written command list that drifts from the registry. | Workers or Controller could receive stale authority text. | Source/card coverage must flag unbacked command text. |
| B2 | A registry row permits a command/event that no runtime branch can handle. | The UI or role prompt would advertise an impossible action. | Install/source check must cross-reference registry rows to Router handlers. |
| B3 | A runtime event exists but no prompt slice can legally tell any role to emit it. | The system becomes unreachable even though the Router accepts the event. | Event capability rows must include producer role and prompt surface owner. |
| B4 | `allowed_external_events` includes a registered event whose prerequisite is false. | Router waits for an event that cannot currently be recorded. | Event-contract model and runtime validator reject false-precondition waits. |
| B5 | `pm_registers_current_node_packet` is accepted for a parent/module node. | Parent/backward repair can jump into leaf-only packet dispatch. | New event-capability model and Router node-kind check reject it. |
| B6 | Parent backward replay repair targets a leaf dispatch event. | The repair bypasses parent-safe replay/segment-decision protocol. | New event-capability model rejects parent-origin repair to leaf events. |
| B7 | Repair `success`, `blocker`, and `protocol_blocker` rows collapse onto one business event. | Reviewer blocker/protocol outcomes become indistinguishable from success. | Repair-transaction and event-capability models reject collapsed rows. |
| B8 | A blocker/protocol outcome uses a success-only business event. | Router may close a failed repair as complete. | Event-capability model checks outcome-row eligibility. |
| B9 | Wait target role does not match event producer role. | Controller delivers a wait to a role that cannot emit the awaited event. | Existing wait producer-role check remains mandatory. |
| B10 | ACK/check-in events appear in `allowed_external_events`. | Mechanical receipt could replace semantic PM/reviewer decisions. | Event-contract model and prompt/card checks keep ACKs separate. |
| B11 | Output contract next recipient diverges from Router event producer. | Valid role output could be routed to the wrong next actor. | Router-action/output-contract checks cover recipient drift. |
| B12 | Active-holder fast-lane commands leak into ordinary role prompts. | A non-holder worker could attempt privileged packet actions. | Command-refinement/card coverage maps fast-lane commands to holder-only scope. |
| B13 | Controller receives or repeats sealed body details while handling control blockers. | Controller would become a hidden project worker. | Existing router-loop/startup-control hazards remain in the verification set. |
| B14 | A generated prompt slice drops role scope or phase scope. | A role sees commands valid elsewhere and acts out of phase. | Prompt generation tests must include role, phase, node kind, and repair origin. |
| B15 | A manual card change reintroduces duplicated authority text. | Future edits drift from the table again. | Source checks should require registry references for authority sections. |
| B16 | New registry rows conflict with existing peer route-replanning changes. | Parallel AI improvements could be overwritten or made unreachable. | Focused runtime route-replanning tests run after every Router edit. |
| B17 | Local installed FlowPilot remains stale after repo changes. | The next local run would still use old prompts/router logic. | Install sync, install audit, and install check run sequentially at the end. |

## FlowGuard Coverage Matrix

| Risk group | Primary model/check | Required proof before production edits |
| --- | --- | --- |
| Event capability by node kind and repair origin | `flowpilot_event_capability_registry_model.py` | Safe scenarios pass; hazards B5-B8 are detected. |
| Registered/currently receivable waits | `flowpilot_event_contract_model.py` | Existing hazards for unknown events, false prerequisites, ACK waits, and material three-exit repairs remain passing. |
| Repair transaction outcome semantics | `flowpilot_repair_transaction_model.py` | Hazards for parent repair target mismatch and collapsed outcome rows remain detected. |
| End-to-end Router loop order | `flowpilot_router_loop_model.py` | Hazards for parent current-node packet registration, parent repair target mismatch, and collapsed repair outcomes remain detected. |
| Route-replanning peer changes | `flowpilot_route_replanning_policy_model.py` | Active node missing and root-like route repair-node hazards remain detected. |
| Prompt/card authority drift | `card_instruction_coverage_model.py`, future generated-slice source checks | Prompt surface must reference registry-derived authority rather than uncontrolled duplication. |
| Command and action refinement | `flowpilot_command_refinement_model.py`, `flowpilot_router_action_contract_model.py` | Command rows, Controller actions, and output contracts remain mutually consistent. |
| Local install freshness | `scripts/check_install.py`, install audit | New model/doc artifacts are present in source and installed skill checks. |

## Pre-Implementation Architecture Fit Check

The current Router architecture can support the first slice, but only with a
bounded adaptation:

- `EXTERNAL_EVENTS` is the current event registry with 92 events. It already
  stores prerequisite flags and has one active-node metadata row:
  `pm_registers_current_node_packet` forbids active nodes with children.
- Parent/current-node safety is not centralized today. The concrete
  `pm_registers_current_node_packet` writer already rejects parent/module nodes,
  but control-blocker waits and repair outcome-table construction can still name
  an incompatible event before that writer runs.
- Material dispatch repair already has three real outcome events:
  `router_direct_material_scan_dispatch_recheck_passed`,
  `router_direct_material_scan_dispatch_recheck_blocked`, and
  `router_protocol_blocker_material_scan_dispatch_recheck`.
- Generic `event_replay` repairs currently use one rerun target for success,
  blocker, and protocol-blocker rows. That is the unsafe overlap being removed.
- Because existing PM repair contracts and tests use generic `event_replay`, the
  safe landing is not to delete the generic lane. The safe landing is to give it
  distinct non-success event identities and validate all three events before any
  wait or repair transaction is persisted.
- Route-replanning changes from peer work are compatible with this slice: they
  operate around route mutation/activation, while this slice gates event waits
  and repair transaction outcomes.

Production implementation therefore follows this compatibility rule:

| Current surface | Landing rule |
| --- | --- |
| Material repair | Keep existing explicit three-outcome material events. |
| Generic control-blocker `event_replay` | Success is the rerun target; blocker and protocol blocker use dedicated PM control-blocker outcome events. |
| Parent/backward repair | Rerun target and outcome events must be parent-safe; leaf packet/current-node events are rejected before persistence. |
| Existing writer validation | Keep writer-specific validation as a second line of defense; do not loosen existing validators. |

## Execution Rules

1. Run real FlowGuard import preflight before behavior-bearing edits.
2. Add and run the event-capability registry model before changing Router code.
3. Treat a model hazard as useful only if it names the bad condition directly;
   do not weaken invariants to make the plan pass.
4. Use background execution for long broad suites, but keep narrow model and
   targeted runtime tests in the foreground after each slice.
5. Preserve peer-agent changes. Do not reset, revert, or rewrite unrelated
   modified files.
6. Sync local install and local git only after all targeted checks pass.
