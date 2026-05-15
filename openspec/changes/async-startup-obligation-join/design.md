# Design: Async Startup Obligation Join

## Boundary

This change is a routing/synchronization change, not a new startup subsystem.
Startup obligations remain ordinary Router-owned work items:

- Controller actions are recorded in `runtime/controller_action_ledger.json`.
- System-card deliveries create ordinary pending card returns.
- Role ACKs are submitted through the existing card check-in path.
- Router observes the same ledgers and returns the same wait/remediation action
  when a required ACK is still missing.

## Startup Dispatch Rule

Router may defer a startup-scope pending-card-return wait only when the next
available action is another independent startup delivery or startup mechanical
action that does not depend on the pending ACK.

Router must not defer:

- non-startup card ACK waits;
- ACK waits for the same role event that is being recorded;
- formal packet ACK preflight waits;
- PM startup activation approval, repair, or dead-end events;
- route/material work after startup unless the startup join is clean.

## Startup Join Rule

Startup activation is the join point. Before PM activation decisions are
accepted, Router must use the existing pending-return dependency blocker to
check startup-scope ACKs. If any startup-scope ACK remains pending, Router
rejects the activation event with the same control-blocker shape used for other
pending card returns and returns/remediates through the ordinary pending-card
return action.

## Same Table Requirement

The implementation must not create a separate startup table or special
Controller-owned state. Startup is attached to the existing runtime interaction
contract:

- Router decides the next row.
- Controller performs only the row Router authorized.
- Controller receipts update the action ledger.
- Role card ACKs update the card runtime pending-return ledger.
- Router synchronizes those ledgers before deciding whether the startup gate is
  clear.

## FlowGuard Model

The startup optimization model must distinguish:

- independent startup dispatch while startup ACKs are pending;
- ACK join checked through the common ledger path;
- PM activation blocked before a clean startup ACK join;
- route/material work blocked before PM activation opens startup.

Known-bad states must fail when startup route work starts before the join,
PM activation happens before the join, or the optimization requires a separate
startup-only wait table.
