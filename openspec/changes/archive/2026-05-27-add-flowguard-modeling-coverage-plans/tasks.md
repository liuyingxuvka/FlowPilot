## 1. OpenSpec And FlowGuard Model Boundary

- [x] 1.1 Validate the new OpenSpec change after proposal, design, specs, and task artifacts exist.
- [x] 1.2 Add a focused FlowGuard model for startup snapshot, PM product/process modeling plans, product/process model families, child-skill projection, route activation, and terminal closure.
- [x] 1.3 Add known-bad hazards for missing snapshot, missing Product Modeling Plan, unreasoned single-model overcollapse, manifest-only model coverage, missing Process Modeling Plan, route activation before accepted families, and final closure with unresolved families.

## 2. Templates And Cards

- [x] 2.1 Add run templates for `flowguard/capability_snapshot.json`, `flowguard/product_modeling_plan.json`, and `flowguard/process_modeling_plan.json`.
- [x] 2.2 Update PM product architecture/product behavior decision cards to require startup snapshot and Product Modeling Plan references.
- [x] 2.3 Update Product Officer card to require product model family coverage, merge/skip reasons, and snapshot references.
- [x] 2.4 Update PM child-skill manifest guidance to map ordinary child skills after accepted product model family evidence.
- [x] 2.5 Update PM route/process cards and Process Officer card to require Process Modeling Plan and process model family coverage.
- [x] 2.6 Update final ledger guidance to close all model families before completion.

## 3. Runtime And Install Checks

- [x] 3.1 Add a lightweight source/artifact check that verifies the new templates and card language exist.
- [x] 3.2 Wire the focused FlowGuard check into install/self-check coverage without touching peer-owned packet-review flow changes.
- [x] 3.3 Preserve compatibility with Reviewer-only child-skill manifest approval while preventing manifest-only model-family closure.
- [x] 3.4 Wire Router startup to generate a portable run-scoped FlowGuard capability snapshot and add runtime tests for non-user-specific skill resolution.

## 4. Verification

- [x] 4.1 Run OpenSpec validation for this change.
- [x] 4.2 Run the focused modeling coverage FlowGuard checks.
- [x] 4.3 Run focused card/template/install tests for touched behavior.
- [x] 4.4 Start Meta and Capability regressions in `tmp/flowguard_background/` and inspect completion artifacts before claiming pass.
- [x] 4.5 Run install check, repo-owned install sync, install audit/check, and smoke validation as practical. Smoke fast was attempted and recorded, but the broad smoke suite is blocked by the existing `flowpilot_model_hierarchy` release gate for `flowpilot_persistent_router_daemon`, not by the startup snapshot path.

## 5. Sync And Local Version

- [x] 5.1 Recheck git status and stage only files owned by this change.
- [x] 5.2 Sync the installed local FlowPilot skill from repo-owned source and verify source freshness.
- [x] 5.3 Create a local git commit for this scoped change without staging unrelated peer-agent work.
