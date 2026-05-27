## Why

Controller packet relay rows can currently be marked done after chat/path handoff without the runtime relay mutation that writes `controller_relay`, packet ledger holder/status, and active-holder lease evidence. That lets Router discover the missing evidence only after receipt reconciliation retries, producing a control blocker for a mechanical relay omission instead of a direct Controller repair path.

## What Changes

- Add a first-class Controller-facing runtime relay command for packet and result envelopes that signs the envelope, updates packet ledger holder/status, and returns machine-checkable relay evidence without opening sealed bodies.
- Require Router packet relay actions to carry explicit runtime relay operations for each packet/result envelope, including expected packet ids, target roles, ledger writes, and active-holder lease expectations where applicable.
- Tighten Controller receipt reconciliation so a `done` receipt for relay actions is not accepted unless Router can verify runtime relay evidence; missing relay evidence must become a Controller-owned mechanical repair action before any PM/control-blocker escalation.
- Update Controller prompts/cards so path-only chat, self-attested receipts, and display-only packet paths are explicitly not valid relay evidence for any packet/result relay action.
- Add FlowGuard bad-case coverage and regression tests for `receipt_done_without_controller_relay_signature`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `stateful-controller-postconditions`: Relay postconditions require verified runtime relay evidence before a Controller receipt can close the postcondition.
- `packet-open-authority-exits`: Worker packet open authority remains blocked until the addressed envelope has a valid Controller relay signature and holder/status state.
- `controller-ledger-table-prompt`: Controller ledger rows for packet/result relay must instruct runtime relay before receipt, not chat/path-only handoff.
- `router-internal-mechanical-actions`: Missing runtime relay evidence is a Controller-owned mechanical repair/replay path when the packet files are otherwise valid.
- `blocker-repair-policy`: PM/control-blocker escalation is reserved for semantic repair, corrupted/invalid packet state, repeated Controller mechanical repair failure, or no legal Controller repair path.

## Impact

- Runtime entrypoints: `skills/flowpilot/assets/flowpilot_runtime_args.py`, `skills/flowpilot/assets/flowpilot_runtime_commands.py`.
- Packet relay helpers and active-holder lease flow: `skills/flowpilot/assets/packet_runtime_relay.py`, `skills/flowpilot/assets/packet_runtime_active_holder_lease.py`.
- Router action payloads and receipt reconciliation: packet work action builders, controller receipt packet folds, scheduled receipt reconciliation, and control-blocker routing helpers.
- Prompts/cards: Controller action ledger prompt and Controller role card.
- Validation: FlowGuard controller receipt evidence fold / packet open authority models, focused router packet tests, packet runtime tests, prompt coverage tests, install sync checks, and applicable meta/capability checks.
