## ADDED Requirements

### Requirement: Controller patrol surfaces repeat break-glass reminder
FlowPilot SHALL include the same short, restrictive break-glass reminder in
Controller daemon-monitor and patrol surfaces used during long foreground
standby.

#### Scenario: Daemon status carries reminder
- **WHEN** Router writes `runtime/router_daemon_status.json` for an active run
- **THEN** the status includes a Controller-visible break-glass reminder with
  the playbook path and ordinary-defect exclusion

#### Scenario: Patrol timer carries reminder
- **WHEN** Controller runs the patrol timer command and receives a nonterminal
  patrol output
- **THEN** the output includes the break-glass reminder with the playbook path
  and ordinary-defect exclusion

#### Scenario: Continuous standby payload carries reminder
- **WHEN** Router exposes `continuous_controller_standby`
- **THEN** the standby row or payload includes the break-glass reminder while
  keeping standby as an in-progress monitor duty, not a finishable checklist
  item
