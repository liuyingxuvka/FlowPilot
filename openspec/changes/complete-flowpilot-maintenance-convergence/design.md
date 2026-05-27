## Context

The current maintenance map reports:

- strict OpenSpec validation passes for all active changes and specs;
- duplicate validation artifacts are present but governed by a read-only audit;
- `.flowpilot` has stale candidates, but the current run pointer is live and
  must be protected;
- runtime owner modules still include FlowGuard-recognized hotspots that can be
  contracted only with facade-preserving splits and fresh evidence.

This pass treats OpenSpec as the scope ledger and FlowGuard as the behavior
preservation gate.

## Model

Represent the maintenance workflow as:

`Maintenance input x repository state -> Set(maintenance output x repository state)`

Core states:

- `preflight_validated`: KB, OpenSpec, FlowGuard import, coordination, and
  current repo state are fresh.
- `archive_candidates_verified`: completed changes are valid and ready to move
  into tracked archive storage.
- `report_only_cleanup_recorded`: duplicate artifacts and runtime retention are
  reported without deletion or rewrite.
- `hotspot_split_pending`: StructureMesh owns a candidate runtime-owner split
  with public facade compatibility requirements.
- `evidence_running`: focused tests and background model regressions are in
  progress with complete log artifacts required before completion.
- `install_synced`: repo-owned installed skill files match the repository.
- `local_git_finalized`: intended files are staged and committed locally only.

Forbidden states:

- `evidence_deleted`: validation or runtime evidence is removed during this
  pass.
- `facade_contract_broken`: a public runtime import, router export, or data
  contract disappears.
- `completion_without_install_sync`: source changes are claimed done before
  installed skill freshness is verified.
- `remote_publication`: pushing, tagging, deploying, or releasing happens as
  part of this maintenance pass.

## Implementation Approach

1. Create this OpenSpec change and validate it strictly.
2. Archive validated completed active changes while preserving tracked files.
3. Record duplicate-artifact and runtime-retention audit outcomes as evidence,
   not cleanup actions.
4. Split only proven `skills/flowpilot/assets/` runtime-owner hotspots into
   child modules with the original module kept as the compatibility facade.
5. Run focused syntax, router, structure, and model-test checks, then launch
   heavyweight Meta and Capability regressions under the stable background log
   contract.
6. Update version/changelog/handoff or maintenance evidence notes as needed.
7. Sync the local installed FlowPilot skill, audit freshness, validate
   OpenSpec, review git scope, and commit locally without pushing.

## Validation

- OpenSpec strict validation for this change and the whole repository.
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- FlowPilot maintenance map, validation artifact audit, and runtime retention
  report.
- Focused router/PM-role and source-contract tests for touched runtime-owner
  modules.
- FlowGuard model-test alignment and structure-maintenance checks.
- Background `run_meta_checks` and `run_capability_checks` artifacts under
  `tmp/flowguard_background/`, including stdout, stderr, combined, exit, meta,
  timestamp, and proof-reuse status.
- Local install sync and freshness audit.
- Local git staged scope and commit.
