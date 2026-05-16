## Context

The repository now has a clean worktree, FlowGuard imports successfully, and
the latest commit includes the dispatch recipient gate work. OpenSpec still
contains many completed change directories plus a few task-count-incomplete
entries, and the repo has large ignored `.flowpilot/` and `tmp/` runtime
trees. The main runtime file and router runtime tests are still very large, so
the first cleanup should prefer small, reversible structure improvements.

FlowGuard applicability decision: `use_flowguard`.

Risk intent: this maintenance pass guards against three failure modes:

- treating local runtime evidence as source and accidentally deleting or
  publishing it;
- hiding or losing completed OpenSpec evidence while cleaning the active list;
- reporting local install or model confidence without source-fresh checks and
  executable validation evidence.

## Goals / Non-Goals

**Goals:**

- Keep completed OpenSpec history available while reducing active-list noise.
- Add read-only maintenance reports before any future destructive cleanup.
- Make one low-risk duplicate source path delegate to a single source of truth.
- Move a focused subset of router startup tests into its own file.
- Preserve and report FlowGuard/background regression evidence.
- Sync and verify the installed local FlowPilot skill after code/docs changes.

**Non-Goals:**

- Do not change the frozen FlowPilot acceptance contract.
- Do not redesign the router protocol, packet ledger, or role authority model.
- Do not delete `.flowpilot/`, `.flowguard/`, `tmp/`, validation results, or
  archive directories during this pass.
- Do not publish, push, tag, or release remotely.

## Decisions

1. **Archive instead of deleting completed OpenSpec changes.**
   Completed changes move under `openspec/changes/archive/2026-05-16-*` so the
   active list is readable while the historical proposal/spec/task evidence
   remains in git.

2. **Read-only reports before cleanup.**
   Validation artifact and runtime-retention tools report duplicates, sizes,
   and candidate stale paths. They do not remove files by default, which keeps
   cleanup reviewable and avoids damaging current local evidence.

3. **Small source-of-truth consolidation first.**
   The first code structure change should target exact duplicate helper paths
   with a wrapper/delegation pattern. Larger router extraction remains a later
   refactor after tests and FlowGuard regressions stay green.

4. **Background heavy model checks, foreground focused checks.**
   Focused tests run synchronously for quick feedback. Heavy FlowGuard
   regressions run through `tmp/flowguard_background/` using the repository's
   stdout/stderr/combined/exit/meta contract.

5. **Install sync is part of done.**
   After source changes, run the repo-owned local install sync and freshness
   audit so the installed Codex skill matches this checkout.

## Risks / Trade-offs

- **Archive move hides a still-active change** -> Only move changes that
  `openspec list` reports as complete; leave task-count-incomplete entries in
  place unless their task files are explicitly completed later.
- **Wrapper import changes script behavior** -> Keep CLI entry behavior and add
  focused tests/import checks around the delegated script.
- **Long regressions consume time** -> Run heavy models in the background with
  stable artifacts, then inspect exit evidence before reporting completion.
- **Line-ending policy creates noisy diffs later** -> Add `.gitattributes`
  without re-normalizing the full tree in this pass.
