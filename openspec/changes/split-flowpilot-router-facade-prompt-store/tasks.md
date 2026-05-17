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
- [ ] 3.5 Move bootloader/startup helpers into bootloader/startup modules.
- [x] 3.6 Move event identity helpers into event modules.
- [ ] 3.7 Move control-blocker and repair-transaction helpers into their modules.
- [ ] 3.8 Move PM role-work, packet dispatch, route frontier, and terminal ledger
  helpers into their modules as independent state owners become clear.

## 4. Documentation, Install Sync, And Validation

- [x] 4.1 Update docs and handoff notes with the new split map.
- [x] 4.2 Run focused tests and FlowGuard checks.
- [x] 4.3 Run router-route, Meta, and Capability checks in background where
  practical and inspect final artifacts.
- [x] 4.4 Synchronize the local installed FlowPilot skill.
- [x] 4.5 Stage and commit the local repository version on `main`.

## Deferred Split Notes

The remaining 3.x split items are intentionally still active. The current pass
landed the low-risk PromptStore/facade wave plus the follow-up ACK return,
event identity, and daemon runtime modules. Bootloader/startup helpers, external
event dispatch settlement, control-blocker repair transactions, PM role-work,
packet dispatch, frontier, and terminal ledgers still share state ownership in
`flowpilot_router.py`; they should move only after their owner contracts are
modeled, rather than by one-function-per-file extraction.
