## 1. Model And Contract

- [x] 1.1 Extend focused FlowGuard card-envelope coverage for gate ACK clearance, work-packet ACK preflight, reminder-only recovery, and ACK-not-work-completion hazards.
- [x] 1.2 Run the focused FlowGuard card-envelope checks and preserve the result JSON.

## 2. Router Implementation

- [x] 2.1 Add ACK clearance scope/reminder metadata to committed system-card and bundle pending-return records.
- [x] 2.2 Ensure missing ACK wait actions remind the role to complete the original runtime ACK loop and do not advertise duplicate delivery as normal recovery.
- [x] 2.3 Add target-role ACK preflight metadata for formal work-packet relay actions without treating ACKs as target work completion.

## 3. Validation And Sync

- [x] 3.1 Add focused Router runtime tests for missing ACK reminder behavior and work-packet preflight semantics.
- [x] 3.2 Run focused non-heavy validations, excluding `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` by user request.
- [x] 3.3 Sync the local installed FlowPilot skill, run install checks, record adoption/KB notes, and commit all intended local plus peer-agent changes.
