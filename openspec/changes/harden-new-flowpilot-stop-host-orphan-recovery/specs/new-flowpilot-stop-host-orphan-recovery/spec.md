## ADDED Requirements

### Requirement: New runtime stop and cancel write terminal lifecycle fences
The new FlowPilot runtime SHALL expose stop and cancel commands that persist a
terminal lifecycle fact for the active run before foreground exit is allowed.

#### Scenario: User stop settles the active run without claiming completion
- **WHEN** `flowpilot_new.py stop` is invoked for a running new-runtime run
- **THEN** the run ledger MUST record `lifecycle_status=stopped_by_user`
- **AND** active leases MUST be closed with terminal reason `stopped_by_user`
- **AND** open, assigned, or acknowledged packets MUST be marked stopped
- **AND** lifecycle guard and foreground duty MUST allow terminal return only
  because the run is stopped, not because project closure completed.

#### Scenario: User cancel settles the active run without claiming completion
- **WHEN** `flowpilot_new.py cancel` is invoked for a running new-runtime run
- **THEN** the run ledger MUST record `lifecycle_status=cancelled_by_user`
- **AND** active leases MUST be closed with terminal reason `cancelled_by_user`
- **AND** open, assigned, or acknowledged packets MUST be marked cancelled
- **AND** final status MUST distinguish cancellation from successful completion.

### Requirement: Host liveness reports override stale progress
The new FlowPilot runtime SHALL treat explicit current host liveness as a
separate lease signal from progress, and SHALL use the latest host liveness
signal when classifying result waits.

#### Scenario: Missing host after progress routes recovery
- **WHEN** an active lease previously recorded `still_working` progress
- **AND** a later host-liveness report records `not_found`, `cancelled`, or
  `timeout_unknown`
- **THEN** lifecycle guard MUST classify the packet wait as recoverable
  liveness failure
- **AND** foreground duty MUST be `recover_or_reissue`, not `wait_patrol`.

#### Scenario: Completed host with no result is no-output
- **WHEN** a host-liveness report records `completed_without_result` or
  `no_output` for an acknowledged packet with no accepted result
- **THEN** lifecycle guard MUST classify the wait as no-output recovery
- **AND** the runtime MUST not mark the packet accepted from the host status
  alone.

### Requirement: Orphan mechanical evidence becomes a recovery duty
The new FlowPilot runtime SHALL detect metadata-only mechanical evidence that
completed without a formal result envelope and route it to recovery instead of
waiting forever or auto-accepting the packet.

#### Scenario: FlowGuard runner summary exists without result envelope
- **WHEN** a FlowGuard or mechanical packet is waiting for a result
- **AND** the run root contains a runner summary for that packet whose recorded
  commands all exited successfully
- **AND** the packet still has no accepted result
- **THEN** lifecycle guard MUST classify the wait as orphan evidence recovery
- **AND** foreground duty MUST be `recover_or_reissue`
- **AND** packet completion MUST still require a formal result submission.

#### Scenario: Incomplete runner summary does not become orphan success
- **WHEN** a runner summary is missing, malformed, in progress, or has a
  nonzero command exit
- **THEN** the runtime MUST NOT treat it as completed orphan evidence
- **AND** ordinary wait, liveness check, or liveness failure rules still apply.
