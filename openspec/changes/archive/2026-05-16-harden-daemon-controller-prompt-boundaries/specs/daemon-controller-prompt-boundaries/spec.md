## ADDED Requirements

### Requirement: Daemon-mode prompts prohibit manual Router metronomes

After the Router daemon is started or attached, FlowPilot prompt text SHALL state that normal progress comes from daemon status and the Controller action ledger, not from foreground `next`, `apply`, or `run-until-wait` calls.

#### Scenario: Controller ledger is quiet while daemon is live
- **WHEN** Controller sees no executable Controller row and daemon status is live or waiting
- **THEN** prompt text MUST direct Controller to standby/watch daemon status and MUST NOT direct Controller to call `next`, `apply`, or `run-until-wait` as the normal progress mechanism

#### Scenario: Controller row completes
- **WHEN** Controller completes a ready Controller action ledger row
- **THEN** prompt text MUST define the completion path as performing the row and writing a Controller receipt, not calling a Router metronome command between rows

### Requirement: Bootloader prompts distinguish pre-daemon startup from daemon-owned runtime

FlowPilot launcher guidance SHALL distinguish the minimal pre-daemon bootloader phase from daemon-owned startup and runtime.

#### Scenario: Minimal startup before daemon
- **WHEN** the formal startup has not yet started or attached the Router daemon
- **THEN** prompt text MAY tell the bootloader to execute Router-provided startup actions needed to create the run shell, current pointer, run index, and daemon

#### Scenario: Startup after daemon
- **WHEN** the Router daemon has started or attached
- **THEN** prompt text MUST state that startup UI, roles, heartbeat binding, Controller-core handoff rows, and later runtime rows are exposed through the Controller action ledger under Router daemon ownership

### Requirement: Resume prompts attach to daemon state and ledger

Heartbeat and manual-resume prompts SHALL describe re-entry as attaching to current-run daemon status, daemon lock, and Controller action ledger, with repair only when daemon evidence is missing or stale.

#### Scenario: Heartbeat wakes with live daemon
- **WHEN** a heartbeat or manual wakeup occurs and the daemon lock/status are live
- **THEN** prompt text MUST direct Controller to attach to the existing daemon and process only exposed Controller rows or standby

#### Scenario: Heartbeat wakes with stale daemon
- **WHEN** a heartbeat or manual wakeup occurs and daemon lock/status are missing or stale
- **THEN** prompt text MAY direct a daemon repair or restart from persisted current-run state and MUST NOT start a second Router writer while a live daemon lock exists

### Requirement: Prompt-boundary FlowGuard rejects ambiguous authority states

FlowPilot SHALL include a focused FlowGuard check that rejects prompt-boundary states where daemon-mode Controller guidance authorizes or implies manual Router progress.

#### Scenario: Known-bad run-until-wait prompt
- **WHEN** a daemon-mode prompt tells Controller to prefer `run-until-wait` for normal progress
- **THEN** the focused FlowGuard check MUST reject that state

#### Scenario: Known-bad return-to-router resume prompt
- **WHEN** a heartbeat/manual-resume prompt tells Controller to continue or return to the router loop without daemon/ledger attachment wording
- **THEN** the focused FlowGuard check MUST reject that state

#### Scenario: Valid daemon-ledger prompt set
- **WHEN** the prompt set says daemon-mode progress uses daemon status, Controller ledger rows, Controller receipts, and standby
- **THEN** the focused FlowGuard check MUST accept the prompt set
