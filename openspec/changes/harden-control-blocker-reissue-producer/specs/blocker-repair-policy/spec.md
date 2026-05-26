## ADDED Requirements

### Requirement: PM same-gate repair selects an executable producer path
FlowPilot SHALL require PM same-gate repair decisions to select an executable repair transaction path that can produce the named return event.

#### Scenario: Same-gate repair text is not enough
- **WHEN** PM selects `same_gate_repair` and describes a worker reissue in `repair_action`
- **THEN** Router MUST treat that text as policy explanation only
- **AND** Router MUST require `repair_transaction.plan_kind` and plan-specific fields that create or reference the follow-up event producer.

#### Scenario: Incomplete PM repair decision stays on PM
- **WHEN** PM submits a same-gate repair decision whose executable transaction cannot produce the named `rerun_target`
- **THEN** Router MUST reject the PM repair decision mechanically
- **AND** Router MUST keep the active blocker targeted at PM for a corrected repair decision rather than moving the wait to workers.

#### Scenario: PM can choose terminal or follow-up blocker instead of rework
- **WHEN** PM determines that no safe producer can be created for the same gate
- **THEN** PM MAY choose an explicit terminal stop, protocol blocker, follow-up blocker, route mutation, or another supported executable plan
- **AND** Router MUST record that outcome through the existing blocker repair policy instead of creating an empty wait.
