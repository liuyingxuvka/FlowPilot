## ADDED Requirements

### Requirement: Fake AI rehearsal covers stop, host loss, no-output, and orphan evidence
The fake AI control rehearsal suite SHALL exercise the new stop/cancel,
host-liveness, no-output, and orphan-evidence recovery paths through public
new-runtime CLI commands.

#### Scenario: Public rehearsal stops a nonterminal run
- **WHEN** a fake project run is stopped before packet completion
- **THEN** public status MUST show a stopped terminal lifecycle
- **AND** final preflight MUST allow foreground exit without claiming project
  closure.

#### Scenario: Public rehearsal reports host not found after progress
- **WHEN** a fake background role first records progress and later reports
  `not_found`
- **THEN** the rehearsal MUST observe `recover_or_reissue`
- **AND** the packet MUST remain incomplete until a formal result is submitted.

#### Scenario: Public rehearsal detects orphan FlowGuard evidence
- **WHEN** fake runner evidence is written for a waiting packet without a
  formal result
- **THEN** the rehearsal MUST observe orphan-evidence recovery
- **AND** the packet MUST not be accepted from runner metadata alone.
