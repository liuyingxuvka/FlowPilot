## ADDED Requirements

### Requirement: Final confidence separates repository confidence from exit authority

FlowPilot final-confidence aggregation SHALL report repository evidence confidence and formal Controller exit authority as separate evidence rows. A formal exit claim MUST require current terminal-return evidence from `flowpilot_new.py final-preflight`.

#### Scenario: Repository evidence passes but startup intake blocks exit

- **WHEN** repository evidence rows are current and passing
- **AND** `flowpilot_new.py final-preflight` reports `allowed=false` with `next_action:open_startup_intake`
- **THEN** final-confidence SHALL NOT report full formal exit confidence
- **AND** the result SHALL expose the terminal-return blocker without treating startup intake as failed test evidence.

#### Scenario: Terminal return authorizes exit claim

- **WHEN** `flowpilot_new.py final-preflight` reports `allowed=true`
- **AND** `foreground_duty.action=terminal_return`
- **AND** `controller_stop_allowed=true`
- **THEN** final-confidence MAY include formal exit authority if all other required evidence rows are current and passing.

### Requirement: Terminal-return evidence uses the public FlowPilot entrypoint

The terminal-return evidence row SHALL execute or consume output from the public `flowpilot_new.py final-preflight` entrypoint. It MUST NOT infer stop authority from status projection, chat history, stale run files, or repository test results alone.

#### Scenario: Status projection looks healthy but preflight is nonterminal

- **WHEN** status output has no active blockers
- **AND** final-preflight reports a nonterminal foreground duty
- **THEN** terminal-return evidence SHALL be blocked
- **AND** the blocker SHALL name the final-preflight duty or next action that prevents exit.

#### Scenario: Diagnostic repository-only run scopes out exit authority

- **WHEN** a diagnostic caller explicitly disables terminal-return requirement
- **THEN** final-confidence SHALL mark formal exit authority as scoped out
- **AND** it MUST NOT describe the result as formal FlowPilot exit confidence.
