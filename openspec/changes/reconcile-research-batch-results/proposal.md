## Why

The control-plane review found an existing FlowPilot gap: durable packet batch
refresh already recognizes that a `research` batch has `results_joined`, but
Router does not fold that durable evidence into the existing
`worker_research_report_returned` event before selecting the next action. That
leaves the Controller waiting or reminding workers after all research result
envelopes already exist.

This change upgrades the current Router reconciliation barrier rather than
creating a parallel research completion daemon or Controller-owned state
writer.

## What Changes

- Extend existing durable wait evidence reconciliation so joined research
  packet batches synthesize the existing Router event
  `worker_research_report_returned` from validated result envelopes.
- Keep Router and Controller visibility metadata-only: packet and result
  bodies remain sealed to the addressed role or PM.
- Keep the existing research next-action flow: after the event is reconciled,
  the existing `relay_research_result_to_pm` action remains the PM relay path.
- Prevent stale research waits and reminders from surviving after the durable
  batch is already joined.
- Preserve the Controller wait-receipt audit as an observer only; it must not
  replace Router-owned reconciliation.

## Impact

- Affected runtime helpers:
  `flowpilot_router_work_packets_next_actions.py`,
  `flowpilot_router_expected_waits_reconciliation.py`, and
  `flowpilot_router_system_cards_selection_reconcile.py`.
- Affected tests: focused router runtime material/research flow tests.
- Affected evidence: FlowGuard control-plane state consistency checks, router
  runtime focused tests, install sync/audit, and local installed skill copy.
