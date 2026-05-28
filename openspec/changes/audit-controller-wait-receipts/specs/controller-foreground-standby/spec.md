## ADDED Requirements

### Requirement: Standby wakeups include wait receipt audit
Controller foreground standby SHALL run the wait receipt audit whenever it is
awake, the run is nonterminal, and Router daemon status exposes an active wait.

#### Scenario: Standby continues an ordinary wait
- **WHEN** standby observes an active wait
- **AND** the wait receipt audit reports `no_formal_return_seen`
- **THEN** standby may continue quiet waiting under the existing anti-exit rules.

#### Scenario: Standby detects ready Controller work from audit
- **WHEN** standby observes an active wait
- **AND** the wait receipt audit reports `formal_return_ready`
- **THEN** standby returns a state that causes Controller to re-read the Controller action ledger and process ready rows from the top.

#### Scenario: Standby detects control-plane stuck audit
- **WHEN** standby observes an active wait
- **AND** the wait receipt audit reports a control-plane stuck classification
- **THEN** standby exposes the audit result in Controller metadata
- **AND** Controller MUST NOT final-answer or silently close the foreground run.
