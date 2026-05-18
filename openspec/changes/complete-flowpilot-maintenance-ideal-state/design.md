## Overview

This change treats "ideal state" as an evidence-backed maintainability state, not an endless line-count chase. Runtime modules are already under the StructureMesh threshold, so further runtime splits are allowed only when a clear owner boundary and external contract test exist. The primary remaining work is to make models, tests, scripts, peer changes, and documentation equally easy to navigate.

## Scope Boundaries

- In scope:
  - Completed peer-agent changes that the user explicitly asked to include.
  - Maintenance maps and diagnostics that make bug localization mechanical.
  - Low-risk model/test/script splits when the parent can remain a compatibility facade.
  - Focused external contract tests and install checks needed for any moved boundary.
- Out of scope:
  - GitHub push, tag, or release publication.
  - Destructive cleanup, broad formatting, dependency churn, or behavior rewrites.
  - Splitting every large declarative model file purely for line count when no safe ownership boundary is current.

## Structure Strategy

1. Start from current evidence: full model-test-code diagnostic, large-file inventory, OpenSpec status, and local install freshness.
2. Validate peer-completed work before adopting it into the final commit.
3. Create a maintainability map that records:
   - runtime owner module count and line-size distribution;
   - facades and script entrypoints;
   - model and test large-file pressure;
   - diagnostic coverage and remaining accepted debt;
   - recommended future split rules.
4. Apply only bounded refactors whose parent facade, public command, or external contract remains stable.
5. Rerun diagnostics after edits, because proof fingerprints and source-contract scan paths can become stale after facade movement.

## Validation Strategy

- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- Focused checks for peer-completed OpenSpec changes.
- `openspec validate complete-flowpilot-maintenance-ideal-state --strict`.
- Focused tests for any touched runtime/model/test/script boundary.
- `python simulations\run_flowpilot_model_test_alignment_checks.py --json-out simulations\flowpilot_model_test_alignment_results.json`.
- Meta/Capability checks when project-control or capability-routing behavior is touched.
- `python scripts\run_test_tier.py --tier fast --json`.
- `python scripts\install_flowpilot.py --sync-repo-owned --json`, `python scripts\audit_local_install_sync.py --json`, `python scripts\install_flowpilot.py --check --json`, and `python scripts\check_install.py --json`.

## Peer Safety

The final commit may include peer-agent work only after its OpenSpec and focused validation evidence is current. If a peer change is incomplete or failing, fix it within its own files and record that evidence before staging.
