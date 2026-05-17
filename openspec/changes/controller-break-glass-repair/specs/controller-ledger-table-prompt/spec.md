## ADDED Requirements

### Requirement: Controller table prompt repeats narrow break-glass reminder
FlowPilot SHALL include a short break-glass reminder and playbook path in each
generated `runtime/controller_action_ledger.json` `controller_table_prompt`
without weakening the existing row-order, receipt, sealed-body, gate, and
foreground-attachment instructions.

#### Scenario: Work board names break-glass path
- **WHEN** Router rebuilds `runtime/controller_action_ledger.json`
- **THEN** `controller_table_prompt.text` includes the path
  `skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`

#### Scenario: Work board limits break-glass scope
- **WHEN** Controller reads `controller_table_prompt.text`
- **THEN** the prompt states that break-glass is only for normal FlowPilot
  control flow that appears broken, stuck, looping, or unable to produce a
  legal next action
- **AND** it states not to use break-glass for ordinary project bugs, worker
  defects, review failures, or normal PM repair
