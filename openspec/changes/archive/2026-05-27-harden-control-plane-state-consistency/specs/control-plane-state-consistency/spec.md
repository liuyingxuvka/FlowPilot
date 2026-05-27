## ADDED Requirements

### Requirement: Router reconciles durable control-plane state before next action

FlowPilot SHALL reconcile durable control-plane ledgers into a consistent Router projection before computing new Controller work, passive waits, dispatch-recipient waits, or control blockers.

#### Scenario: Receipt flag and durable batch lifecycle diverge
- **WHEN** a Controller receipt proves material scan results were relayed to PM
- **AND** `router_state.flags.material_scan_results_relayed_to_pm` is true
- **AND** the durable active material batch still reports `results_joined`
- **THEN** Router MUST reconcile the batch lifecycle to `results_relayed_to_pm` or emit a control blocker naming the missing durable evidence
- **AND** Router MUST NOT reject PM material disposition solely from the stale batch lifecycle

#### Scenario: Superseded PM role-work remains active
- **WHEN** a PM role-work request declares `supersedes_request_id`
- **THEN** Router MUST move the superseded request to a terminal status
- **AND** Router MUST remove the superseded request from active request and lifecycle indexes
- **AND** the superseded request MUST NOT count as target-role busy for replacement dispatch

#### Scenario: Next action uses derived projection
- **WHEN** durable ledgers and `router_state` projections disagree
- **THEN** Router MUST compute the next action from the reconciled durable projection
- **AND** the unreconciled projection MUST NOT be used as authority to emit a wait, dispatch, or blocker

### Requirement: Control-plane stale-save protection

FlowPilot SHALL prevent a daemon snapshot from overwriting newer foreground Router state or durable event evidence.

#### Scenario: Foreground updates state during daemon tick
- **WHEN** the daemon loaded `router_state` at version N
- **AND** a foreground event writes version N+1 before the daemon saves
- **THEN** the daemon MUST reload and merge current durable facts before saving
- **AND** it MUST NOT replace version N+1 with the older in-memory snapshot

### Requirement: Derived metadata remains stable across reconciliation

FlowPilot SHALL derive wait reminder and result self-check metadata from stable durable records.

#### Scenario: Wait reminder already sent for same wait identity
- **WHEN** the same wait identity is still active
- **AND** a persisted last-reminder timestamp is within the configured cooldown
- **THEN** Router MUST NOT materialize a duplicate wait reminder action

#### Scenario: Result body contains a contract self-check section
- **WHEN** a result body contains `# Contract Self-Check` or `## Contract Self-Check`
- **THEN** the result envelope self-check metadata MUST record the self-check as completed
- **AND** it MUST apply the existing pass/fail content checks to that section
