## 1. Model Hardening Gate

- [x] 1.1 Add focused FlowGuard prompt-boundary model coverage for daemon-mode prompt authority.
- [x] 1.2 Add known-bad hazards for `run-until-wait` as a normal daemon-mode metronome, broad return-to-router heartbeat resume, unclear-next-step router fallback, and Controller row-to-row router command use.
- [x] 1.3 Add a safe scenario for current daemon-first startup: minimal run shell/current/index before daemon, then daemon-owned startup rows through Controller ledger.
- [x] 1.4 Run the focused FlowGuard check and confirm known-bad hazards fail while the safe prompt plan passes.
- [x] 1.5 Record that Meta and Capability heavyweight simulations are skipped by user direction.

## 2. Prompt Source Updates

- [x] 2.1 Update `skills/flowpilot/SKILL.md` launcher, `run-until-wait`, heartbeat/manual wakeup, and Controller-boundary wording.
- [x] 2.2 Update Controller role card wording for `controller_local_action`, unclear next step handling, standby, and partial table reads.
- [x] 2.3 Update generated Controller action ledger table prompt text in `flowpilot_router.py`.
- [x] 2.4 Update generated heartbeat prompt text in `flowpilot_router.py`.
- [x] 2.5 Update heartbeat template text in `templates/flowpilot/heartbeats/hb.template.md`.
- [x] 2.6 Keep all edits prompt-only; do not change daemon scheduling or duplicate-row reconciliation behavior.

## 3. Verification

- [x] 3.1 Run focused prompt/source checks covering the changed prompt text.
- [x] 3.2 Run focused FlowGuard checks for daemon/controller prompt boundaries.
- [x] 3.3 Run focused daemon/two-table checks that are small enough for this prompt boundary; daemon reconciliation live-conformance still reports the out-of-scope repeated-row issue owned by the parallel repair.
- [x] 3.4 Skip `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` by user direction.

## 4. Sync And Finish

- [x] 4.1 Sync the local installed FlowPilot skill from the repository.
- [x] 4.2 Verify installed skill freshness and local install health.
- [x] 4.3 Check git state and preserve peer-agent changes.
- [x] 4.4 Update FlowGuard adoption notes with touched boundary, commands, skipped heavy checks, and residual risk.
- [x] 4.5 Run KB postflight and record any reusable lesson or gap.
