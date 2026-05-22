## MODIFIED Requirements

### Requirement: Foreground Controller standby
Foreground Controller standby SHALL keep the Controller attached during
nonterminal waits while exposing a bounded internal state-policy boundary for
state and foreground-mode decisions.

#### Scenario: Standby state policy is internally split without changing behavior
- **WHEN** FlowPilot computes foreground standby from terminal status, user
  requirement, daemon liveness, pending Controller actions, and wait-target
  conditions
- **THEN** the standby parent still exposes the existing helper names and
  public standby/patrol result shapes
- **AND** the child state-policy module MUST map the full input matrix only to
  the declared standby states and foreground modes
- **AND** the child module MUST NOT become a second daemon, ledger, scheduler,
  or Router progress authority
