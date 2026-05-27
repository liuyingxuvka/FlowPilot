## MODIFIED Requirements

### Requirement: Router reconciles before choosing next action or blocker
FlowPilot SHALL run a reconciliation barrier before every daemon next-action decision, manual next-action decision, and control-blocker creation.

#### Scenario: Valid startup display receipt exists before next action
- **WHEN** Controller has a done receipt for `write_display_surface_status`, the startup display artifacts validate for the current run, and `startup_display_status_written` is false
- **THEN** Router MUST reclaim the display postcondition, set `startup_display_status_written=true`, mark matching action and scheduler rows reconciled, and compute the next action from the updated state
- **AND** Router MUST NOT enqueue another ordinary `write_display_surface_status` row for the same scope

#### Scenario: Already-reconciled stateful row has stale flag
- **WHEN** a Controller action or scheduler row is already Router-reconciled and names a registered stateful postcondition whose Router-owned flag is false
- **THEN** Router MUST replay or reclaim that postcondition during reconciliation before next-action selection
- **AND** if the postcondition cannot be validated, Router MUST create bounded repair/blocker evidence instead of treating the row as complete or issuing a duplicate ordinary command

#### Scenario: Receipt folding precedes startup intake release
- **WHEN** startup `user_intake` release depends on startup activation and startup activation depends on pre-review reconciliation
- **THEN** Router MUST fold all startup-local Controller receipt postconditions into authoritative run state before deciding whether startup activation remains blocked
