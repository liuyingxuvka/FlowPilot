## Context

FlowPilot has a broad FlowGuard suite, but the current validation surface is uneven. Most specialized models are small and focused, while `simulations/meta_model.py` and `simulations/capability_model.py` have grown into heavyweight monoliths:

- `simulations/results.json`: 1,949,768 states and 2,010,665 edges for the meta model.
- `simulations/capability_results.json`: 1,959,064 states and 2,036,030 edges for the capability model.
- The next largest persisted model result is under 10,000 states.

The project already has `flowpilot_model_mesh_model.py`, but that model validates authority across model evidence and live run facts. It does not partition the oversized parent graphs or define how child models cover parent responsibilities.

There are active peer-agent changes in runtime, daemon, packet, and card files. This change should first add independent hierarchy artifacts and only touch shared validation surfaces after focused checks pass.

## Goals / Non-Goals

**Goals:**

- Introduce an executable parent/child hierarchy contract for FlowPilot FlowGuard models.
- Classify heavyweight parents, shared kernels, focused child models, evidence tiers, freshness rules, partition ownership, and background regression obligations.
- Make unsafe split plans fail before the repository relies on child evidence.
- Allow foreground checks to use lightweight hierarchy evidence while full meta/capability regressions run in background with the standard log contract.
- Preserve full heavyweight regressions as release-level or forced checks until the thin-parent migration is complete.
- Keep final git submission inclusive of compatible peer-agent work, without reverting unrelated changes.

**Non-Goals:**

- Do not immediately delete or rewrite the existing `meta_model.py` or `capability_model.py` graphs.
- Do not merge child models into another monolithic graph.
- Do not change FlowPilot runtime behavior unless hierarchy integration exposes a narrow validation hook.
- Do not treat hierarchy pass, proof reuse, or background liveness as proof that full meta/capability regressions passed.

## Decisions

### Add a Dedicated Hierarchy Model

Create `simulations/flowpilot_model_hierarchy_model.py` and `simulations/run_flowpilot_model_hierarchy_checks.py`.

Rationale: The existing mesh model answers whether model/live evidence can authorize continuation. The new hierarchy model answers whether the model set is partitioned safely enough to reduce heavyweight parent reliance.

Alternative considered: extend `flowpilot_model_mesh_model.py`. Rejected because authority checks and split-boundary checks have different failure modes; mixing them would make the existing mesh less inspectable.

### Treat Meta and Capability as Legacy Heavyweight Parents

The initial hierarchy should register:

- `meta`: process-control parent; currently heavyweight; still requires full regression or valid proof for release confidence.
- `capability`: capability-routing parent; currently heavyweight; still requires full regression or valid proof for release confidence.
- Existing focused models as child evidence sources grouped by startup/control, router/daemon/resume, packet/role, child-skill/capability, terminal/ledger, and evidence/mesh.

Rationale: This matches the observed size distribution. Only two models are too heavy; most other models are already useful children.

### Require Partition Coverage and Ownership Checks

The hierarchy model must encode parent-space items such as startup, material intake, product architecture, crew/heartbeat, router/daemon, packets/roles, child-skill routing, terminal ledger, evidence credibility, and install/sync evidence. Every item must be assigned to exactly one child, parent, read-only dependency, or shared kernel.

Rationale: Parent/child hierarchy only reduces risk if gaps and overlap are visible.

### Keep Heavy Runs Background-Friendly

Meta/capability full checks remain valid but should be launched through `tmp/flowguard_background/` when they are too slow for foreground work. The hierarchy runner must not claim those checks passed unless their result/proof artifacts are current.

Rationale: The user explicitly wants long model regressions in the background while foreground work continues.

### Integrate Gradually With Install and Smoke

Add the hierarchy check to validation surfaces as a fast foreground check. Keep `smoke_autopilot.py --fast` proof reuse for slow checks and ensure `scripts/check_install.py` verifies the new hierarchy artifacts.

Rationale: This provides immediate safety without requiring every local install check to rebuild two million-state graphs.

## Risks / Trade-offs

- Parent model confidence may be overclaimed if child coverage is mistaken for full regression. Mitigation: hierarchy output must include explicit `heavy_parent_full_regression_required` or proof-current status.
- Sibling child models may overlap on state writes or side effects. Mitigation: encode overlap hazards and ownership failures in the hierarchy model.
- Active peer-agent changes may touch shared validation files. Mitigation: start with independent new files, then patch shared surfaces narrowly after rereading them.
- Existing result files may be stale. Mitigation: use result/proof freshness rules and background artifacts instead of trusting path existence.
- The first iteration does not make `meta_model.py` and `capability_model.py` thin. Mitigation: tasks separate immediate hierarchy safety from later parent graph extraction.

## Migration Plan

1. Add the hierarchy model and runner.
2. Add hierarchy specs and focused checks.
3. Integrate the hierarchy runner into coverage/install/smoke surfaces with minimal patches.
4. Launch meta/capability full checks in background using standard artifacts or reuse valid proofs only when fingerprints match.
5. Sync installed FlowPilot skill after repository validation.
6. Preserve and stage compatible peer-agent changes together at final git submission time.

Rollback is straightforward: remove the new hierarchy artifacts and validation references. Existing meta/capability runners remain intact.
