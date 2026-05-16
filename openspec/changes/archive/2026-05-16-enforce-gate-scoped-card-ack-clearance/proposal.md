## Why

FlowPilot system-card ACKs are read receipts for prompt/control context, not proof that the addressed work is complete. As the Router becomes more autonomous, it needs a durable rule for clearing required ACKs at route gates and before formal work packets so it neither advances on unread system context nor overreacts with PM repair or duplicate card delivery.

## What Changes

- Add scoped ACK clearance for system cards at route gate/node boundaries and before formal work-packet relay to a role.
- Treat missing required ACKs as a lightweight reminder to acknowledge the original committed card or bundle, not as target-work completion failure and not as a reason to duplicate the original system card.
- Preserve the existing Controller-owned delivery receipt boundary: Controller can mark that it relayed a card or packet, but Router only treats target-role work as complete after the target role returns the required report/result event.
- Add focused FlowGuard coverage and runtime tests for missing ACK before gate/work advancement, reminder-only recovery, and duplicate-delivery prevention.

## Capabilities

### New Capabilities
- `system-card-ack-clearance`: Defines scoped system-card ACK clearance, reminder-only recovery, and the relationship between card ACKs, gate progress, and work-packet relay.

### Modified Capabilities
- None.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused Router runtime tests for system-card ACK waits and work-packet preflight behavior.
- Affected models: new focused FlowGuard model/runner for ACK clearance; existing heavyweight meta and capability regressions are intentionally not run for this change.
- No public CLI contract change for role ACK submission; roles still use the existing runtime card open/ack commands and existing expected ACK paths.
