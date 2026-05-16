# controller-receipt-foreground-guard Specification

## Purpose
TBD - created by archiving change repair-controller-receipt-foreground-guard. Update Purpose after archive.
## Requirements
### Requirement: Display receipts update Router-owned display facts

FlowPilot SHALL reconcile a done Controller receipt for `sync_display_plan`
into both the Controller action ledger and the Router-owned display sync fact
before Router computes the next action.

#### Scenario: Receipt-only display sync does not repeat

- **WHEN** Router has a pending `sync_display_plan` action
- **AND** Controller writes a valid done receipt for that action
- **THEN** Router MUST update the same display sync facts written by direct
  `sync_display_plan` application
- **AND** Router MUST NOT reissue the same display sync action solely because
  the prior Router-owned display fact stayed stale

### Requirement: Foreground exit is blocked by ready Controller actions

FlowPilot SHALL treat ready Controller actions as foreground work, not as a
safe foreground stop or ordinary role wait.

#### Scenario: Controller action ready blocks foreground exit

- **WHEN** the Router daemon is live
- **AND** the Controller action ledger contains a pending executable action
- **THEN** foreground standby MUST return `controller_action_ready`
- **AND** the returned metadata MUST say foreground exit is not allowed
- **AND** the returned metadata MUST say `foreground_required_mode` is
  `process_controller_action`
- **AND** the returned metadata MUST say Controller stop is allowed only after a
  terminal run
- **AND** Controller MUST process the pending action before ending or entering
  ordinary role standby

#### Scenario: Live daemon with no ready action requires standby

- **WHEN** the Router daemon is live
- **AND** the Controller action ledger has no executable action
- **AND** the run is not terminal, user-required, or daemon-stale
- **THEN** foreground Controller MUST remain attached through standby instead
  of ending the user-visible turn
- **AND** the returned metadata MUST say `foreground_required_mode` is
  `watch_router_daemon`
- **AND** the returned metadata MUST NOT mark Controller stop as allowed
