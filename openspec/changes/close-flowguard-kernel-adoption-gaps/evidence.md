## Evidence Notes

### FlowGuard external-contract gap

- `python -m unittest tests.test_flowpilot_runtime_gateway_adoption.FlowPilotRuntimeGatewayAdoptionTests.test_gateway_classifies_and_blocks_wrong_owner_for_critical_state tests.test_flowpilot_controller_wait_receipt_audit.ControllerWaitReceiptAuditUnitTests.test_audit_marks_formal_return_ready_when_next_notice_exists -v`
  - Result: pass, 2 tests.
- `python -c "... _source_contract_plan_report() ..."`
  - Result: `ok=true`, `finding_count=0`.
- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out tmp/flowguard_kernel_alignment_check.json`
  - Result: exit 0, `ok=true`, `alignment_ok=true`, `source_audit_ok=true`,
    `full_diagnostic_ok=true`, `release_convergence_ok=true`,
    `internal_only_count=0`.
  - Remaining `full_coverage_ok=false` is from deferred structure-split
    findings, not unresolved external-contract gaps.

### Legacy data and old logic disposition

- `python scripts/check_install.py --json`
  - Result: `ok=true`.
  - Legacy equivalence checks are current:
    `flowpilot_legacy_to_router_equivalence_valid`,
    `flowpilot_barrier_equivalence_results_valid`, and
    `flowpilot_legacy_prompt_to_cards_matrix_valid` all pass.
  - Retired watchdog paths are absent.
  - Optional legacy root state files are either valid when present
    (`.flowpilot/current.json`, `.flowpilot/index.json`) or validly absent for
    old root-scoped state/capability/route files.
- `python scripts/audit_local_install_sync.py --json`
  - Result: `ok=true`.
  - Legacy cockpit source is not tracked and absent from the main tree.
  - Retired watchdog/supervisor sources are absent from the main tree.
- `python scripts/install_flowpilot.py --check --json`
  - Result: `ok=true`.
  - Required dependencies are installed, including real `flowguard`.

Disposition: no behavior-bearing legacy code was deleted in this pass. The
remaining `legacy` references in docs, equivalence matrices, tests, and
compatibility facades are current compatibility or audit evidence, while the
remaining oversized runtime modules are deferred StructureMesh debt and should
not be rewritten under this FlowGuard-kernel adoption closure scope.

### Validation and local install acceptance

- `python -m unittest tests.test_flowpilot_runtime_gateway_adoption tests.test_flowpilot_controller_wait_receipt_audit -v`
  - Result: pass, 12 tests.
- `openspec validate --all --strict --json --no-interactive`
  - Result: 164 passed, 0 failed.
- Background `tmp/flowguard_background/run_meta_checks.*`
  - Result: `status=passed`, exit code `0`, final stdout/stderr/combined/exit/meta
    artifacts present, `proof_reused=false`.
- Background `tmp/flowguard_background/run_capability_checks.*`
  - Result: `status=passed`, exit code `0`, final stdout/stderr/combined/exit/meta
    artifacts present, `proof_reused=false`.
- `python scripts/install_flowpilot.py --install-missing --sync-repo-owned --json`
  - Result: `ok=true`; repo-owned `flowpilot` was already fresh.
- `python scripts/audit_local_install_sync.py --json`
  - Result: `ok=true`; installed skill fresh, legacy cockpit absent, retired
    watchdog/supervisor sources absent.
- `python scripts/check_install.py --json`
  - Result: `ok=true`; selected legacy/equivalence/retired-path checks pass.

### Local git boundary

- Final `git status --short --branch` still shows a dirty worktree because peer
  agents are actively changing sibling maintenance areas.
- This change's owned files are:
  - `openspec/changes/close-flowguard-kernel-adoption-gaps/`
  - `simulations/flowpilot_model_test_alignment_source_code_contracts.py`
  - `simulations/flowpilot_model_test_alignment_source_test_evidence.py`
  - an appended entry in `docs/flowguard_adoption_log.md`
- Peer or pre-existing dirty files remain visible and were not reverted,
  normalized, staged, committed, or cleaned up by this pass.
- No local commit was created because the shared dirty worktree includes active
  peer-agent changes, including newly changed final-confidence and packet-result
  maintenance surfaces.
