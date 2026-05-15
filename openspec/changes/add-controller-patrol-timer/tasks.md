## 1. Model And Contract

- [x] 1.1 Add a focused FlowGuard model for Controller patrol timer anti-exit behavior.
- [x] 1.2 Run the focused FlowGuard patrol checks and preserve the result artifact.
- [x] 1.3 Record the FlowGuard adoption note with Meta/Capability explicitly skipped by user direction.

## 2. Runtime Implementation

- [x] 2.1 Add a `controller-patrol-timer` CLI command that waits, reads the existing monitor, and returns patrol outcomes.
- [x] 2.2 Extend standby payloads with `required_command`, anti-exit purpose, rerun-and-wait loop rule, and forbidden completion evidence.
- [x] 2.3 Preserve existing Router daemon monitor ownership and avoid using `next`, `apply`, or `run-until-wait` as the patrol metronome.

## 3. Prompt Hardening

- [x] 3.1 Update the Controller role card with the exact patrol command and foreground anti-exit duty.
- [x] 3.2 Update the Controller resume/reentry card with the exact patrol command and rerun-and-wait rule.
- [x] 3.3 Update the generated `controller_table_prompt` with the exact patrol command and rerun-and-wait rule.
- [x] 3.4 Ensure the final `continuous_controller_standby` row payload names the exact command at task time.

## 4. Tests And Sync

- [x] 4.1 Add runtime tests for quiet monitor `continue_patrol`, new work wakeup, terminal exit, and prompt/payload command text.
- [x] 4.2 Run focused pytest coverage for Controller standby and patrol timer behavior.
- [x] 4.3 Synchronize the local installed FlowPilot skill and run install/audit checks.
- [x] 4.4 Record skipped heavyweight Meta/Capability checks and residual risk.
