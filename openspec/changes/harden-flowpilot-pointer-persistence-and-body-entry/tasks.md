- [x] 1. Baseline and coordination
  - [x] 1.1 Preserve peer-agent changes and record current dirty worktree scope.
  - [x] 1.2 Verify FlowGuard engine, project audit, and OpenSpec change status.
  - [x] 1.3 Identify existing model/test owners for pointer persistence, body entry, prompt policy, and Cartesian coverage.

- [x] 2. FlowGuard model and coverage upgrade
  - [x] 2.1 Add pointer persistence/recovery axes and oracles to the existing control-plane Cartesian model.
  - [x] 2.2 Add body transport/body shape axes and oracles to the current-contract or integration Cartesian model.
  - [x] 2.3 Project new pointer/body cases through ContractExhaustionMesh and TestMesh ownership.
  - [x] 2.4 Update Model-Test Alignment obligations for owner code surfaces and ordinary tests.
  - [x] 2.5 Refresh generated model result artifacts after focused model checks pass.

- [x] 3. Runtime pointer persistence and recovery
  - [x] 3.1 Add a small pointer helper under `flowpilot_core_runtime` that reuses existing Router JSON atomic persistence semantics without adding pointer business fields.
  - [x] 3.2 Replace direct `current.json` and `index.json` writes in run shell creation and status refresh.
  - [x] 3.3 Implement unambiguous pointer recovery for corrupt current/index files.
  - [x] 3.4 Preserve corrupt backups as diagnostics only and keep current/index JSON shapes unchanged.
  - [x] 3.5 Add focused pointer corruption, lock, ambiguity, and no-new-field tests.

- [x] 4. submit-result body entry hardening
  - [x] 4.1 Add `--body-file` and exactly-one body-source parsing to the public CLI.
  - [x] 4.2 Validate body input as a top-level JSON object before run ledger load or packet mutation.
  - [x] 4.3 Add structured, safe body-entry feedback for malformed, non-object, stringified, empty, or unreadable payloads.
  - [x] 4.4 Add focused CLI tests proving object acceptance and pseudo-JSON rejection without normalization.

- [x] 5. Prompt/card synchronization
  - [x] 5.1 Update runtime-kit prompt sources to prefer `submit-result --body-file`.
  - [x] 5.2 Regenerate or update generated role/phase/event/system cards that include the shared return policy.
  - [x] 5.3 Update prompt/card coverage tests so raw `--body <sealed_result_summary>` is no longer the default.

- [x] 6. Validation, install sync, and topology
  - [x] 6.1 Run focused runtime, CLI, prompt, Cartesian, ContractExhaustionMesh, and Model-Test Alignment tests.
  - [x] 6.2 Run meta and capability checks, using background logs if needed and inspecting final artifacts before claiming pass.
  - [x] 6.3 Rebuild and check FlowGuard topology after model/test/code/prompt changes.
  - [x] 6.4 Sync repo-owned installed FlowPilot skill and run local install audits/checks.

- [x] 7. Local git closure
  - [x] 7.1 Re-check worktree and separate owned changes from peer/untracked work.
  - [x] 7.2 Stage only this change's intended files.
  - [x] 7.3 Create a scoped local commit if all required routine evidence is current.
- [x] 7.4 Record KB postflight observation and report evidence, skipped checks, residual risk, and claim boundary.
