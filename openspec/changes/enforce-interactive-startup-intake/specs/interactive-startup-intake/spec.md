## ADDED Requirements

### Requirement: Formal startup accepts only interactive native intake
FlowPilot formal startup SHALL accept a confirmed startup intake result only when the result, receipt, and envelope identify the launch as interactive native UI, mark `headless` as false, and mark `formal_startup_allowed` as true.

#### Scenario: Interactive native intake is accepted
- **WHEN** Router validates a confirmed startup intake result whose result, receipt, and envelope declare `launch_mode: interactive_native`, `headless: false`, and `formal_startup_allowed: true`
- **THEN** Router records startup answers and may continue deterministic startup bootstrap

#### Scenario: Missing interactive provenance is rejected
- **WHEN** Router validates a confirmed startup intake result missing interactive launch provenance
- **THEN** Router rejects the result before recording startup answers or creating downstream startup side effects

### Requirement: Headless intake cannot satisfy formal startup
FlowPilot formal startup MUST reject startup intake output produced by headless, scripted, automatic-confirmation, or synthesized paths, even when the file shape, answer enums, and body hash are otherwise valid.

#### Scenario: Headless confirmed result is rejected
- **WHEN** Router validates a confirmed startup intake result whose launch metadata declares `launch_mode: headless`, `headless: true`, or `formal_startup_allowed: false`
- **THEN** Router rejects the result with an error explaining that formal startup requires the native interactive startup UI

#### Scenario: Headless helper remains diagnostic only
- **WHEN** the startup intake helper is invoked with `HeadlessConfirmText` or `HeadlessCancel`
- **THEN** it writes artifacts that identify the launch as headless and not allowed for formal startup

### Requirement: Controller must stop instead of substituting intake
The FlowPilot Controller SHALL open the router-provided startup intake UI command for `open_startup_intake_ui` and MUST NOT satisfy the row by auto-confirming, scripting, filling chat text, or directly generating the intake result.

#### Scenario: UI cannot be opened
- **WHEN** the native startup intake UI cannot be opened or does not produce an interactive result
- **THEN** Controller reports the startup UI failure and does not continue formal startup from a substituted result
