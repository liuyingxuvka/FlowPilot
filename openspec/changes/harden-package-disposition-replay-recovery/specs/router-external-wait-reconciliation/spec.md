## ADDED Requirements

### Requirement: Conflicting package replay does not erase legal repair waits

Router external-wait reconciliation SHALL keep the current legal
control-blocker or PM repair wait visible when a stale conflicting PM package
disposition is replayed after that conflict has already been routed to repair.

#### Scenario: Replay occurs while PM repair wait is open

- **GIVEN** the current open wait asks PM to resolve a package-disposition
  conflict
- **AND** stale role-output ledger evidence repeats the same conflicting body
- **WHEN** Router reconciles external waits
- **THEN** Router SHALL keep the PM repair wait open
- **AND** Router SHALL NOT close the wait as successful package absorption.

#### Scenario: Replay occurs while repair follow-up wait is open

- **GIVEN** a PM repair decision has opened a producer-backed follow-up wait
- **AND** stale conflicting package-disposition evidence is replayed
- **WHEN** Router reconciles external waits
- **THEN** Router SHALL keep the follow-up wait tied to the repair transaction
- **AND** Router SHALL NOT regress to the old package conflict as the active
  owner.
