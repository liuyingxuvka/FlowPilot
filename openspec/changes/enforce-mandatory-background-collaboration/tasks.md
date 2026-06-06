## 1. Current Contract Audit

- [x] 1.1 Build an old/new FlowPilot difference table covering startup,
  background role work, resume, recovery, prompt, fake-AI, and test/model
  surfaces.
- [x] 1.2 Classify each residual old symbol as new-required, old-only,
  rename-or-uncertain, or historical-only before deletion.

## 2. Runtime And UI

- [x] 2.1 Make the startup background control a required acknowledgement and
  stop formal startup when it is disabled.
- [x] 2.2 Gate startup, manual resume rehydration, role recovery, and
  background role payload submission on current background role capability.
- [x] 2.3 Remove positive single-agent role-continuity fallback paths and old
  startup/resume event aliases from current runtime code.

## 3. Models, Prompts, And Tests

- [x] 3.1 Update startup, PM review, capability/meta, and prompt-boundary
  models so mandatory background role capability is the only current path.
- [x] 3.2 Rewrite old positive tests for single-agent, heartbeat, and fixed
  startup roles as negative-path tests.
- [x] 3.3 Add fake-AI package coverage for disabled acknowledgement, missing
  capability evidence, old fields, corrected package acceptance, and protected
  state non-advancement.
- [x] 3.4 Update active prompts/cards/UI preview text so they do not describe
  single-agent fallback or old FlowPilot role startup authority.

## 4. Validation And Sync

- [x] 4.1 Run focused startup/router/fake-AI tests after implementation.
- [x] 4.2 Run affected FlowGuard model checks and model-test alignment updates.
- [x] 4.3 Rebuild/check project topology after model/test/code ownership changes.
- [x] 4.4 Sync and audit the local FlowPilot install.
- [x] 4.5 Record FlowGuard adoption evidence and KB postflight, then report git
  state without reverting peer-agent work.

## 5. Current Startup Trunk Cleanup

- [x] 5.1 Keep the 53-work-package current trunk as the only current route:
  user material enters the conversation, Runtime/Router performs mechanical
  startup entry, PM starts the first material decision, roles are opened on
  demand, PM absorbs or repairs, and Runtime advances, blocks, or stops.
- [x] 5.2 Confirm startup has no Reviewer startup fact gate, no PM startup
  activation gate, no heartbeat authority, no fixed six-role prewarm, and no
  old event or field alias as a positive path.
- [x] 5.3 Remove old startup cards and output contracts from the current
  runtime kit manifest, install checks, prompt coverage, and role output
  contract support while preserving explicit negative tests for rejected
  legacy events/output types.
- [x] 5.4 Maintain the current responsibility boundary: Runtime/Router owns
  fields, hashes, paths, current run/node/packet/result ids, role bindings,
  output contract shape, and ledger absorption; Reviewer owns semantic quality;
  FlowGuard operator owns process/model/state reachability; PM owns
  disposition.
- [x] 5.5 Preserve and test the new blocker, repair, stale-result,
  background-unavailable, route-mutation recovery, same-node repair,
  stop/cancel, and protocol-dead-end paths through packet/lease/result/PM
  disposition/Reviewer quality review/Runtime frontier only.
- [x] 5.6 Complete FieldLifecycleMesh coverage for top-level, middle, and leaf
  fields with current, mechanical-runtime-owned, PM-decision-owned,
  reviewer-quality-owned, FlowGuard-process-owned, retired, and
  forbidden-legacy lifecycle states.
