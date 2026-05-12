# FlowPilot Work Authority Upgrade Plan

## Purpose

This plan upgrades FlowPilot from prompt-guided formal returns to
Router-registered work authority.

It does not add a parallel task-lease system. It reuses existing mechanisms:

- `runtime_kit/contracts/contract_index.json` as the work/result contract menu;
- PM role-work requests as PM-requested work packets;
- packet/result envelopes as concrete per-task authority records;
- active-holder lease semantics as the pattern for holder/action/version checks;
- the Router current wait state as the live gate for direct Router returns.

The core rule is:

> Any card or packet that asks a role to do concrete work and return a formal
> result must have Router-registered work authority. Identity/system cards may
> be acknowledged, but they must not authorize formal reports by themselves.

## Current Behavior

| Area | Current Shape | Problem |
| --- | --- | --- |
| Contract table | Knows which role may produce which output contract. | The table does not always become a concrete current-task authority before output. |
| System/role cards | Can explain duties and sometimes ask for concrete work. | A task-like card can look like work but lack a formal return path. |
| Role output runtime | Can prepare and submit role-output envelopes. | For `router_supplied` outputs, a role can still provide an event name manually. |
| Router | Rejects unknown or not-currently-allowed events. | The rejection happens after the role already produced a misleading formal output attempt. |
| PM role-work packet | Already carries strict contract binding and result recipient. | It is not yet the universal path for PM-requested officer/reviewer formal reports. |

## Target Behavior

| Area | Target Shape | Plain Meaning |
| --- | --- | --- |
| Identity card | May require ACK only. | "I received my role rules." |
| Task card or packet | Must carry Router-registered work authority. | "This specific job is assigned to you now." |
| PM-requested officer/reviewer work | Uses PM role-work request and strict output contract binding. | PM asks; Router validates and registers the task. |
| Router-flow task work | Uses Router current wait or packet/active-holder authority. | Router is currently waiting for this role's result. |
| `router_supplied` formal output | May not use role-guessed event names. | AI cannot invent the return door. |
| Formal return | Must prove role, contract, result recipient, and current authority. | Router checks the ticket before accepting the report. |

## Optimization Sequence

| Step | Concrete Change | Boundary |
| --- | --- | --- |
| 1 | Update the FlowGuard dynamic-return-path model to distinguish identity cards, task cards, PM work packets, Router direct waits, and active-holder-style authority. | Model only, no product code. |
| 2 | Add risk scenarios for task-like system cards without work authority, identity cards carrying hidden work, role-guessed router events, wrong-role packet use, wrong contract, stale authority, and mechanical green used as Router acceptance. | Model must catch each listed bug before implementation. |
| 3 | Run the upgraded model and the existing role-output/runtime mesh checks. | Do not treat skipped or stale checks as passes. |
| 4 | Tighten the runtime boundary for `router_supplied` role outputs so a manually supplied event name is accepted only when it is the live Router wait authority; otherwise require packet/work authority. | No new registry. Reuse existing contract and wait state facts. |
| 5 | Tighten PM role-work/packet result handling so PM-requested officer/reviewer reports remain the default formal path and always return to PM. | Preserve existing PM role-work packet format. |
| 6 | Update card/runtime instructions so identity cards say "ACK only" and task-like cards say "use the registered packet/current wait; if missing, report a protocol blocker." | Generated instruction text only; avoid adding long bespoke prompt prose to every card. |
| 7 | Add focused tests for the new boundary: valid PM packet result, valid current wait event, invalid guessed event, task card without authority, wrong role, wrong contract, stale authority. | Keep tests narrow and compatible with other agents' work. |
| 8 | Run installation, smoke, targeted runtime tests, upgraded FlowGuard model, and local sync audit. | Remote GitHub sync is explicitly out of scope. |

## Bug/Risk Checklist

| Risk ID | Possible Bug From This Upgrade | FlowGuard Must Catch |
| --- | --- | --- |
| R1 | A system identity card accidentally authorizes a formal report. | Identity card with formal output accepted. |
| R2 | A task-like system card asks for work but has no registered work authority. | Task card without packet/current wait accepted. |
| R3 | A role guesses a `router_supplied` event name. | Role-guessed event accepted. |
| R4 | An event exists in the registry but is not currently allowed by Router wait state. | Registered-but-not-current event accepted. |
| R5 | Role-output format validation is treated as permission to continue. | Mechanical green becomes Router acceptance. |
| R6 | PM role-work result is returned to the wrong recipient. | PM-requested result does not return to PM. |
| R7 | Wrong role uses a packet/result authority. | Packet holder role mismatch accepted. |
| R8 | A packet uses the wrong output contract for the addressed role/task. | Contract/task/role mismatch accepted. |
| R9 | Stale route/frontier/holder authority is reused after state changed. | Stale authority accepted. |
| R10 | Legacy direct officer events remain the default path and compete with PM packets. | Legacy direct event accepted while PM packet authority exists. |
| R11 | The fix blocks valid fixed-event contracts. | Fixed-event contract falsely rejected. |
| R12 | The fix blocks valid current Router waits. | Direct live Router wait falsely rejected. |
| R13 | The fix blocks valid PM role-work packet results. | PM packet result falsely rejected. |

## FlowGuard Coverage Matrix

| Model/Check | Required Coverage |
| --- | --- |
| `flowpilot_dynamic_return_path_model.py` | R1-R5, R10-R13, and current-run projection for rejected router-supplied outputs. |
| `flowpilot_role_output_runtime_model.py` | Runtime source still binds every role-output contract and distinguishes fixed versus router-supplied event modes. |
| `flowpilot_model_mesh_model.py` | A green child model cannot authorize continuation when packet/current authority is unchecked. |
| `flowpilot_protocol_contract_conformance_model.py` | PM role-work strict binding remains valid and rejects foreign contracts. |
| Runtime unit tests | Concrete CLI/runtime paths enforce the modeled boundary. |

## Implementation Acceptance

Implementation is acceptable only if:

- the upgraded dynamic return-path model accepts valid PM-packet, valid direct
  Router-wait, and valid fixed-event scenarios;
- the model rejects every risk scenario listed above;
- targeted runtime tests pass;
- install check and local install sync audit pass;
- no unrelated peer-agent edits are reverted;
- local installed FlowPilot is synced;
- local git has the finished changes staged/committed if the user still wants
  local git synchronization;
- remote GitHub is not pushed.
