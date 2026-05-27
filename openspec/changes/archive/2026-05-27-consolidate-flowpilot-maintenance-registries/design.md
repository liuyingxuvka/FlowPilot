## Context

The current FlowPilot structure is intentionally model-backed and heavily validated. Recent StructureMesh work reduced the router facade and created many focused owner modules, but the remaining maintenance load has shifted toward repeated tables and alignment manifests:

- install-required files and diagnostic surfaces are tracked in multiple places;
- gate outcome facts are split across reset flags, block events, pass-clear mappings, and compatibility re-exports;
- external events are manually sharded and recombined;
- output-contract and process binding facts appear in both JSON registries and Python tables;
- tests sometimes repeat runtime kit paths that are already present in manifests.

This change treats those repeated facts as registry data first, while preserving the existing runtime behavior and public compatibility surfaces.

## Design Goals

- Reduce repeated maintenance facts without lowering FlowPilot's control standard.
- Keep old imports and names as generated or derived compatibility views.
- Make each phase small enough to verify independently.
- Prefer data/registry extraction over behavior rewrites.
- Keep generated or derived outputs directly comparable to the current tables before switching callers.

## Non-Goals

- Do not remove `flowpilot_router.py` as the public compatibility facade.
- Do not rename event names, schema values, output contract IDs, CLI commands, or ledger shapes.
- Do not weaken Controller foreground patrol, final-answer preflight, worker information isolation, packet/body visibility, write-lock recovery, or terminal lifecycle ordering.
- Do not merge break-glass helpers into normal router IO.
- Do not run broad formatting or unrelated cleanup.
- Do not push, tag, or publish remotely as part of this change.

## Architecture

### 1. Maintenance Surface Registry

Create a canonical maintenance surface registry that records the facts currently repeated across install checks, maintenance maps, diagnostics, and tests:

- surface id;
- path;
- kind, such as runtime owner, facade, model, script, test, runtime kit asset;
- owning model or StructureMesh region when known;
- compatibility parent/child relationship;
- required install status;
- expected evidence family.

Existing diagnostics should first read this registry in report mode and prove parity with current lists. After parity is established, install checks and maintenance reports can consume the registry directly.

### 2. Gate Outcome Registry

Create one canonical registry row per gate outcome family. Derived compatibility views provide the existing names:

- reset flag tuples;
- `GATE_OUTCOME_BLOCK_EVENT_SPECS`;
- `GATE_OUTCOME_BLOCK_EVENTS`;
- `GATE_OUTCOME_PASS_CLEAR_FLAGS`;
- `GATE_OUTCOME_PASS_CLEARS_EVENTS`.

The initial implementation must compare generated views against current exported values before switching behavior-sensitive callers.

### 3. External Event Registry

Represent each external event once with explicit metadata:

- event name;
- flag;
- phase/family;
- role or authority;
- legacy marker;
- canonical alias relationship when present;
- description.

Existing `EXTERNAL_EVENTS_*` shard names and the merged `EXTERNAL_EVENTS` table remain available as derived compatibility views.

### 4. Contract And Process Binding Registry

Treat `runtime_kit/contracts/contract_index.json` as the primary output-contract source. Python process-binding helpers should derive contract IDs and task-family relationships from the contract index where possible, with explicit Python-only policy fields kept separate.

This avoids duplicating output contract IDs in `PROCESS_CONTRACT_BINDINGS`, packet defaults, and role-output runtime specifications.

### 5. Router Facade Constant Descent

Move remaining policy/catalog constants out of `flowpilot_router.py` only after the relevant catalog registry exists. The router facade continues to re-export old names, but internal owner modules should import the direct catalog where practical instead of relying on router binding for static policy.

### 6. Manifest-Driven Tests

Where tests enumerate runtime card paths only to apply a class-wide rule, load the runtime kit manifest and filter by audience/kind/phase. Keep hand-written paths only where the specific file identity is the contract under test.

## FlowGuard Strategy

- Use the existing structure maintenance model as the parent guard.
- Add focused child evidence or model-test alignment rows for any new registry surface.
- Review `router_target_structure()` and `model_target_structure()` with real FlowGuard before claiming structure correctness.
- Run focused checks after each phase; run background meta/capability regressions before release-readiness claims.

## Verification Strategy

Fast checks:

- compile touched Python files;
- focused unit tests for generated views and compatibility exports;
- model-test alignment checks;
- StructureMesh checks.

Background checks:

- router tier if runtime router behavior is touched;
- `simulations/run_meta_checks.py`;
- `simulations/run_capability_checks.py`.

Background check completion must cite the log root, stdout/stderr/combined/exit/meta paths, exit code, latest update time, completion status, and proof-reuse status when available.

## Rollout

1. Add registry and parity tests without switching runtime callers.
2. Switch low-risk diagnostics and generated reports to the registry.
3. Switch protocol compatibility tables to derived views.
4. Switch selected runtime callers only after table parity is proven.
5. Sync local installed skill and verify source freshness.
6. Commit locally without including unrelated pre-existing changes.

## Risks

- A generated compatibility view may accidentally reorder or omit a legacy key.
  Mitigation: assert equality with the current exported table before switching callers.
- Contract-index derivation could hide Python-only policy that was previously explicit.
  Mitigation: separate contract identity fields from Python-only policy fields.
- Background regressions can be mistaken for completed evidence while still running.
  Mitigation: use the repository background artifact contract and inspect exit/meta files.
- Pre-existing dirty worktree changes may overlap with maintenance files.
  Mitigation: inspect touched files before editing and stage only this change's files.
