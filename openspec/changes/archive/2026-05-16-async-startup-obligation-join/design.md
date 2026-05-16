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
- Reviewer startup fact review before the startup prep join is clean;
- route/material work after startup unless PM startup activation opens it.

## Startup Join Rule

Reviewer live startup fact review is the startup prep join point. Before
`reviewer.startup_fact_check` is delivered or `reviewer_reports_startup_facts`
is accepted, Router must use the existing pending-return dependency blocker to
check the startup prep card ACKs (`pm.core`, PM contract/work-request/phase-map,
and PM startup-intake cards). If any prep ACK remains pending, Router returns
the ordinary pending-card-return wait/remediation action.

The PM startup activation decision does not need a second all-startup join.
After the reviewer report exists, the existing same-role card ACK rule already
blocks `pm_approves_startup_activation`, `pm_requests_startup_repair`, and
`pm_declares_startup_protocol_dead_end` until PM has ACKed
`pm.startup_activation`.

## Same Table Requirement

The implementation must not create a separate startup table or special
Controller-owned state. Startup is attached to the existing runtime interaction
contract:

- Router decides the next row.
- Controller performs only the row Router authorized.
- Controller receipts update the action ledger.
- Role card ACKs update the card runtime pending-return ledger.
- Router synchronizes those ledgers before allowing Reviewer startup review and
  before each same-role event that already depends on a card ACK.

## FlowGuard Model

The startup optimization model must distinguish:

- independent startup dispatch while startup ACKs are pending;
- pre-review ACK join checked through the common ledger path;
- Reviewer startup fact review blocked before a clean startup prep ACK join;
- route/material work blocked before PM activation opens startup.

Known-bad states must fail when Reviewer starts startup review before the prep
join, startup route work starts before PM activation, or the optimization
requires a separate startup-only wait table.
