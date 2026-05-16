## 1. Model And Contract

- [x] 1.1 Update the FlowGuard meta model so scheduled-continuation startup cannot load Controller core before heartbeat binding is recorded.
- [x] 1.2 Add or update model invariants/scenarios that preserve manual-resume startup without heartbeat creation.

## 2. Router Runtime

- [x] 2.1 Move initial run-state creation early enough for startup heartbeat binding before Controller core handoff.
- [x] 2.2 Reorder startup next-action selection so `create_heartbeat_automation` is emitted before `load_controller_core` for scheduled continuation.
- [x] 2.3 Update startup heartbeat action metadata to reflect bootloader/startup ownership rather than Controller main-loop ownership.

## 3. Tests And Sync

- [x] 3.1 Add runtime tests for scheduled heartbeat-before-Controller ordering and manual-resume skip behavior.
- [x] 3.2 Run targeted router tests and FlowGuard checks, fixing any model misses.
- [x] 3.3 Sync the local installed FlowPilot skill and run install/audit checks.
