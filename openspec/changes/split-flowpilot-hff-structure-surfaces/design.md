## Context

The current FlowGuard model-test alignment inventory is green for ordinary
binding evidence. The original HFF batch closed its four deferred StructureMesh
split findings, and the current diagnostics now identify two final
runtime-contract StructureMesh findings in router child modules. The repository
also has active peer-agent work, so this change must keep its own OpenSpec and
implementation scope separate from unrelated dirty files.

The strict FlowPilot maintenance contract remains current-path-only: preserving
an entrypoint means preserving the current supported command or import path. It
does not mean accepting legacy fields, old packet shapes, missing-field
defaults, newest-run fallback, repo-root fallback, or prose/shape guessing.

## Goals / Non-Goals

**Goals:**

- Close the current deferred StructureMesh findings from the executable
  model-test alignment diagnostics, including the two final runtime-contract
  router child modules.
- Keep each parent entrypoint thin enough that ownership is visible and each
  moved responsibility has one child owner.
- Preserve current CLI/module behavior, JSON output contracts, and install
  freshness.
- Run focused validation after each boundary, then refresh broad inventory,
  topology, install, and local git evidence.

**Non-Goals:**

- No release, deploy, push, tag, package publication, or secret handling.
- No migration that teaches runtime or validation code to accept old field
  names, old packet/result shapes, old router paths, or fallback prose.
- No broad cleanup of peer-agent changes outside this change's files.

## Decisions

1. Keep parent files as current entrypoints and move implementation partitions
   into child modules.

   Rationale: the current command/module paths are part of supported repo and
   skill operation. Thin parents keep the public surface stable while
   StructureMesh can evaluate child ownership. Removing the parent paths would
   create unrelated downstream churn; adding compatibility aliases would violate
   the new-only contract.

2. Split by ownership, not by arbitrary line count.

   Rationale: the diagnostic threshold is the trigger, but the repair must be
   model-owned. Each child module should own one cohesive partition such as
   obligation catalog data, code/test binding collection, topology scanning, or
   runtime command orchestration.

3. Treat validation and install sync as ordered evidence.

   Rationale: source edits stale previous diagnostics, topology artifacts, and
   installed skill freshness. Focused checks run near each split; broad
   FlowGuard and install checks run after source stabilization. Install sync
   and install audit are serialized to avoid racing source writes.

4. Leave live-run final confidence blocked when no current run exists.

   Rationale: there is no `.flowpilot/current.json` in this clone. Creating a
   fake current run would violate the single-path evidence rule. The final gate
   may remain blocked only for live-run evidence while structure, model, test,
   topology, and install evidence are current.

## Risks / Trade-offs

- Parent entrypoint imports can accidentally become hidden facades with mixed
  ownership -> Keep parents limited to CLI/import orchestration and verify child
  ownership through focused tests and model-test alignment diagnostics.
- Moving constants/data can change JSON ordering or result shape -> Preserve
  dataclasses and output builders where possible, and run existing contract
  tests plus model runner commands.
- Peer-agent edits can change files during the pass -> Recheck git status
  before install sync and before any git action; do not stage unrelated files.
- Heavy regressions can take time -> Run heavyweight model checks under the
  repository background log contract, then inspect final artifacts before
  claiming evidence.
