## ADDED Requirements

### Requirement: Current work rejects stale pending-action authority
FlowPilot SHALL derive daemon status and current-work ownership only from pending actions that still have durable authority.

#### Scenario: Pending action references a completed wait
- **WHEN** `router_state.pending_action` references a Controller action row or Router scheduler row that is closed, done, reconciled, resolved, superseded, or canceled
- **THEN** daemon status and current status summary MUST NOT report that pending action as `current_work.source=pending_action`

#### Scenario: Durable ledgers identify the next owner
- **WHEN** a stale pending action is rejected and durable ledgers identify a Router, Controller, PM, role, or user responsibility
- **THEN** `current_work` MUST name the durable owner and source rather than the stale pending action

#### Scenario: No durable owner after stale pending rejection
- **WHEN** a stale pending action is rejected and no durable owner can be selected
- **THEN** `current_work` MUST report Router reconciliation or no actionable owner rather than reminding the stale role target
