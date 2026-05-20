## 1. OpenSpec and FlowGuard

- [x] 1.1 Validate this OpenSpec change strictly.
- [x] 1.2 Update focused FlowGuard/control-gate checks so a formal package
  release means path/hash identity plus source packet/output-contract
  recoverability, using existing state concepts where possible.

## 2. Runtime and cards

- [x] 2.1 Update the PM formal gate package writer to preserve existing packet
  envelope and output-contract references inside the current `result_envelopes`
  entries.
- [x] 2.2 Clarify Reviewer cards so Reviewer derives current pass/fail from
  existing packet acceptance slice, output contract, result self-check, and
  node plan when applicable.
- [x] 2.3 Keep missing standards on the existing blocked-review path and keep
  higher-standard ideas on the existing PM suggestion path.

## 3. Verification and sync

- [x] 3.1 Run focused unit tests for PM formal package content, reviewer card
  instruction coverage, and control gates.
- [x] 3.2 Run focused FlowGuard packet/control checks and start heavyweight
  Meta/Capability regressions in the background artifact directory.
- [x] 3.3 Inspect background artifacts for exit code, completion status, latest
  update time, and proof reuse before claiming completion.
- [x] 3.4 Run install check, sync repo-owned FlowPilot assets to the local
  installed skill, and run local install audit/check.
- [x] 3.5 Recheck git status, stage only this task's files, and create the
  requested local git version without absorbing peer-agent work.
