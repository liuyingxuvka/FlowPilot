## Why

FlowPilot can leave a role looking busy when an old Controller passive wait is still open after the real durable evidence has already arrived. The repair must preserve the existing two-class rule: ACK-only system cards clear on ACK, while output-bearing work packages clear only on their required report, result, decision, or packet-spec event.

## What Changes

- Reconcile stale ACK wait rows through the existing Router settlement and Controller-ledger rebuild paths.
- Preserve output-bearing work busy state after ACK until the named output event is recorded.
- Recheck stale passive waits before the dispatch recipient gate treats a role as busy.
- Keep runtime JSON write-in-progress handling as wait/retry, not immediate failure.
- Update focused FlowGuard models and tests for ACK-only versus output-bearing clearance.

## Capabilities

### New Capabilities

### Modified Capabilities

- `dispatch-recipient-gate`: clarify that stale ACK waits may be reconciled only when the right clearing evidence exists, and output-bearing work remains busy until its output event.
- `system-card-ack-clearance`: clarify ACK-only versus output-bearing card clearance behavior.
- `router-external-wait-reconciliation`: require recorded output events to close output-bearing wait rows across all roles.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `simulations/flowpilot_dispatch_recipient_gate_model.py`
- `simulations/flowpilot_two_table_async_scheduler_model.py`
- `simulations/flowpilot_card_envelope_model.py`
- `tests/test_flowpilot_router_runtime.py`
- Focused result JSON files under `simulations/`
- Installed local `flowpilot` skill sync after validation
