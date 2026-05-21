# 2026-05-21 - FlowPilot FlowGuard Test Obligation Ownership

## Evidence Summary

- The change clarifies who owns test decisions in the FlowPilot + FlowGuard
  workflow: PM owns the test obligation matrix and disposition; FlowGuard
  Officers derive model obligations and gaps with the requested FlowGuard
  satellite skills; workers maintain ordinary tests only when their work packet
  explicitly assigns that scope.
- The focused FlowGuard model covers the intended chain from PM skill
  selection, officer reports, worker test coverage, PM disposition, reviewer
  review, and final evidence ledger.
- The installed FlowPilot skill was synchronized from the active repository
  source and independently audited as fresh.

## Commands

- OK: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` ->
  `1.0`.
- OK: `openspec validate clarify-flowguard-test-obligation-ownership --strict`.
- OK: `python simulations\run_flowpilot_test_obligation_ownership_checks.py --json-out simulations\flowpilot_test_obligation_ownership_results.json`.
- OK: `python -m py_compile simulations\flowpilot_test_obligation_ownership_model.py simulations\run_flowpilot_test_obligation_ownership_checks.py`.
- OK: `python -m unittest tests.test_flowpilot_card_instruction_coverage`.
- OK: `python -m unittest tests.test_flowpilot_output_contracts`.
- OK: `python simulations\run_meta_checks.py` via `tmp\flowguard_background\run_meta_checks.*`.
- OK: `python simulations\run_capability_checks.py` via `tmp\flowguard_background\run_capability_checks.*`.
- OK: `python scripts\install_flowpilot.py --sync-repo-owned --json`.
- OK: `python scripts\audit_local_install_sync.py --json`.
- OK: `python scripts\install_flowpilot.py --check --json`.

## Findings

- The previous flow had generic `role_skill_use_bindings`, but did not make
  test-obligation discovery and closure a hard PM-owned chain.
- Officer prose no longer closes a test gap by itself. It must become a row in
  the PM matrix and receive an explicit disposition.
- Ordinary test implementation stays with workers when assigned in the packet;
  broad layered validation routes to TestMesh; model/code/test mismatches route
  to Model-Test Alignment.
- The focused model intentionally rejects unsafe routes such as PM deciding
  test coverage before worker evidence, officers default-maintaining ordinary
  tests, background progress counted as pass, and reviewer/final ledger closure
  before the PM matrix is dispositioned.

## Skipped Or Limited

- No GitHub push, tag, release, deploy, or public publication was performed in
  this local sync round.
- Existing peer changes in shared dirty files were not reverted or staged.
- The legacy full meta/capability regressions reused current proof files where
  the background contract marked them valid.

## Next Actions

- Use this chain as the default FlowPilot rule when PM assigns FlowGuard
  Officers to model/test-sensitive work.
- For future gaps, close one disposition class at a time instead of claiming
  all model coverage from a selected boundary-test fix.
