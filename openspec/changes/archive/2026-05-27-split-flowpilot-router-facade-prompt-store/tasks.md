## 1. OpenSpec And FlowGuard Planning

- [x] 1.1 Create the OpenSpec proposal, design, and requirements.
- [x] 1.2 Verify real FlowGuard import before changing behavior boundaries.
- [x] 1.3 Add an executable FlowGuard split model with known-bad hazards.

## 2. PromptStore First Wave

- [x] 2.1 Add a runtime-kit prompt manifest and initial prompt assets.
- [x] 2.2 Add `flowpilot_prompt_store.py` with strict load/render/hash checks.
- [x] 2.3 Replace selected inline prompt builders with PromptStore calls.
- [x] 2.4 Add focused PromptStore tests and install-check coverage.

## 3. Router Split Waves

- [x] 3.1 Move prompt/card delivery helpers into a prompt-delivery module.
- [x] 3.2 Move card ACK return settlement into a card-returns module.
- [x] 3.3 Move controller action ledger helpers into a controller-ledger module.
- [x] 3.4 Move daemon runtime helpers into a daemon-runtime module.
- [x] 3.5 Move bootloader/startup helpers into bootloader/startup modules
  through the 5.x coarse owner split.
- [x] 3.6 Move event identity helpers into event modules.
- [x] 3.7 Move control-blocker and repair-transaction helpers into their modules
  through the 5.x coarse owner split.
- [x] 3.8 Move PM role-work, packet dispatch, route frontier, and terminal ledger
  helpers into their modules through the 5.x coarse owner split.

## 5. Coarse Phase Facade Convergence

- [x] 5.1 Update the FlowGuard facade split model to require coarse phase
  owners, not only helper extraction.
- [x] 5.2 Move runtime state and startup/bootloader/resume phase-controller bodies into
  `flowpilot_router_runtime_state.py` and
  `flowpilot_router_startup_flow.py`.
- [x] 5.3 Move Controller scheduler/receipt/standby phase-controller bodies into
  `flowpilot_router_controller_scheduler.py`.
- [x] 5.4 Move material/research/current-node packet and PM role-work bodies
  into `flowpilot_router_work_packets.py`.
- [x] 5.5 Move external-event/control-blocker/repair transaction bodies into
  `flowpilot_router_event_dispatcher.py` and
  `flowpilot_router_events_repair.py`.
- [x] 5.6 Move route/frontier/final-ledger/terminal bodies into
  `flowpilot_router_route_frontier.py` and
  `flowpilot_router_terminal_ledger.py`.
- [x] 5.7 Keep `flowpilot_router.py` as the public facade and verify it now
  delegates the coarse phase bodies through compatibility wrappers.

## 4. Documentation, Install Sync, And Validation

- [x] 4.1 Update docs and handoff notes with the new split map.
- [x] 4.2 Run focused tests and FlowGuard checks.
- [x] 4.3 Run router-route, Meta, and Capability checks in background where
  practical and inspect final artifacts.
- [x] 4.4 Synchronize the local installed FlowPilot skill.
- [x] 4.5 Stage and commit the local repository version on `main`.

## Deferred Split Notes

The original 3.x split items are now covered by the 5.x coarse owner modules.
The facade still keeps compatibility wrappers for public/test-facing names, but
the major startup, controller, packet, event/repair, route/frontier, and
terminal phase bodies delegate to owner modules rather than remaining in
`flowpilot_router.py`.
