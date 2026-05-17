## Context

The current checkout is on local `main`, with the previous behavior-preserving
router structure reduction fast-forwarded into it. The repository already has a
FlowGuard structural-refactor model, a FlowGuard adoption log, focused runtime
test entrypoints, and installer/public-boundary checks. The remaining
maintainability hotspots are active Python files that are large or duplicated:

- `skills/flowpilot/assets/flowpilot_router.py` remains around 38k lines.
- `tests/test_flowpilot_router_runtime.py` remains around 15k lines.
- `simulations/capability_model.py` and `simulations/meta_model.py` remain large,
  with several phase helpers above several hundred lines.
- `skills/flowpilot/assets/packet_runtime.py` is a multi-responsibility runtime.
- `scripts/check_install.py` still has heavy check-group bodies.
- `scripts/flowpilot_user_flow_diagram.py` is an exact duplicate of the skill
  asset file and should become a thin wrapper.

This pass is structure-only. It must preserve public entrypoints because cards,
docs, tests, installed skills, and local scripts already reference them.

## Goals / Non-Goals

**Goals:**

- Make active Python files easier to read, review, and test.
- Establish one source of truth for duplicated repository CLI logic.
- Keep old imports and CLI commands working through compatibility facades.
- Reduce large functions by moving cohesive responsibilities into helper
  modules.
- Keep every slice independently verifiable with focused tests or model checks.
- Synchronize the local installed FlowPilot skill after source changes.
- Commit the validated result on local `main`.

**Non-Goals:**

- No product feature additions.
- No protocol, event-name, or persisted JSON-shape changes.
- No route/runtime semantics changes.
- No remote publication, tag, GitHub Release, deploy, or binary package work.
- No deletion of compatibility entrypoints in this pass.

## Decisions

1. Keep `main` as the working branch.

   Rationale: the user explicitly requested direct work on `main` and deletion
   of other local branches. The current main has been fast-forwarded to include
   the completed structural baseline.

2. Use local backup plus git commit history instead of tracked backup copies.

   Rationale: tracked copies of 38k-line files would make the repository harder
   to maintain. Local `tmp/maintenance_backup_main_*` snapshots are enough for
   manual rollback support, while git history is the authoritative rollback.

3. Use facade-first splits.

   Rationale: external callers continue importing and executing current module
   names. New helper modules own smaller domains, while original modules
   re-export or delegate.

4. Handle low-risk source-of-truth cleanup before router hotspot work.

   Rationale: duplicated user-flow diagram code and packet/install/model
   structure can be improved with lower behavior risk than changing the router
   event pipeline first.

5. Treat FlowGuard as a maintenance guard, not a replacement for runtime tests.

   Rationale: the structural model proves ordering and protected boundaries.
   Each code slice still needs production-facing tests/checks for the touched
   boundary.

6. Launch heavy model regressions through the repository background log
   contract when useful.

   Rationale: long Meta/Capability checks should not block local edits when
   independent work can continue, but final reporting must inspect `.out`,
   `.err`, `.combined`, `.exit`, and `.meta` artifacts before claiming pass.

7. Treat Meta and Capability as layered evidence parents by default.

   Rationale: routine maintenance should validate current thin-parent evidence
   and child-model contracts quickly. Full Meta/Capability expansion remains a
   release-grade or explicitly requested background regression obligation, not
   the default foreground confidence path.

## Risks / Trade-offs

- Import drift after splitting modules -> keep the old facade modules and add
  focused import/CLI checks.
- JSON output drift in `check_install.py` -> preserve result keys and severity
  semantics, and run `check_install.py --json` plus public-release checks.
- Router behavior drift -> split helpers behind existing entrypoints and run
  ACK/return, route mutation, terminal, closure, cards, and controller tests.
- Model semantics drift -> run structural guard plus Meta/Capability checks
  when model phase files are touched; compare result status and release
  confidence honestly.
- Evidence hierarchy drift -> drive parent partitions from
  `flowpilot_parent_responsibility_ledger.json` rather than duplicate runner
  maps, and keep routine confidence separate from release confidence.
- Installed skill stale after source changes -> run repository-owned install
  sync, install check, and local installed freshness audit before final commit.
- Scope creep -> no release, no protocol changes, no compatibility deletion, no
  broad cleanup outside named files.
