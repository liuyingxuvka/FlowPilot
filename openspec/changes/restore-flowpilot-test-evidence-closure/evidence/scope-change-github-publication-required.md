# Scope Change: GitHub Publication Required

Recorded: 2026-07-18

## Authority

The maintainer's latest instruction requires the completed FlowPilot upgrade to
be pushed to GitHub and published under a new version after the tests planned
for the frozen task baseline finish.

This instruction supersedes
`scope-change-github-publication-deferred.md`. The older file remains only as
historical scope evidence and no longer authorizes the current closure.

## Current Publication Contract

- Freeze this task at FlowGuard check engine and agent-skill suite `0.58.0`.
- Do not chase or rerun validation solely because another agent later upgrades
  FlowGuard.
- Create one exact task-owned local commit after current local evidence passes.
- Push the task branch.
- Fast-forward the GitHub default branch to that exact commit; never force it.
- Create annotated tag `v0.12.1` on that exact commit.
- Create one source-only GitHub Release for `v0.12.1`.
- Verify the task branch, default branch, tag, version files, and GitHub Release
  all resolve to the same commit and version.
- Treat any non-fast-forward update, tag collision, release collision, or
  commit mismatch as a visible blocker. Do not select an alternate publication
  path.

## Claim Boundary

Publication evidence closes only the repository/version release route. It does
not prove arbitrary future AI behavior or future compatibility with FlowGuard
versions outside the frozen `0.58.0` task baseline.
