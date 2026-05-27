## Why

FlowPilot is locally healthy at v0.9.5, but the remaining release-facing gap is
the structural route repair/replacement policy that decides how failed route
branches are superseded, replayed, and hidden from future completion evidence.
Before syncing local commits to GitHub, this pass also needs a public-boundary
README/privacy check and install freshness verification.

## What Changes

- Add a focused FlowGuard boundary for full route repair/replacement policy:
  return-to-original repair, supersede-original replacement, sibling branch
  replacement, stale-evidence invalidation, frontier rewrite, and completion
  blocking while mutation activation is pending.
- Harden runtime route mutation activation so replacement policies are explicit
  and cannot leave old sibling or superseded evidence acting as current proof.
- Update focused runtime tests, install checks, docs, version metadata, and the
  local installed FlowPilot skill.
- Run public release preflight/privacy checks before remote sync.
- Commit and push the FlowPilot repository branch only. This pass does not tag,
  publish a GitHub Release, package binaries, deploy, or publish companion skill
  repositories.
- Keep Meta and Capability regressions explicitly skipped for this pass because
  the user excluded those heavy model runs; run focused route repair, release,
  install, and smoke checks instead.

## Capabilities

### New Capabilities

- `route-repair-replacement-policy`: route mutation repair/replacement policies
  preserve PM authority, stale-evidence invalidation, frontier rewrite,
  same-scope replay, sibling replacement, and final-ledger blocking.

### Modified Capabilities

- `repository-maintenance-guardrails`: pre-release maintenance includes public
  boundary/privacy checks, installed-skill freshness, local commit, and remote
  branch sync while explicitly excluding tag/release/deploy publication.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- `simulations/` route repair/replacement model and focused runner/results
- `tests/test_flowpilot_router_runtime.py`
- `scripts/check_install.py` and `scripts/check_public_release.py` if needed
- `README.md`, `CHANGELOG.md`, `VERSION`, `HANDOFF.md`, and release/privacy docs
- Local installed FlowPilot skill under the Codex skills directory
- Git branch `main` pushed to `origin` after validation
