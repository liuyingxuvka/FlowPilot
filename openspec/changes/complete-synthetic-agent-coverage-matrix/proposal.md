## Why

FlowPilot now has deterministic synthetic trace replay for the highest-risk
packet/result paths, but the repository still cannot make a full-confidence
claim that every currently modeled, testable AI action branch has an explicit
coverage owner. This change turns the synthetic AI work package into a governed
coverage matrix so missing branches, fixture-only evidence, progress-only
background checks, and remaining structure-split blockers stay visible and
actionable.

## What Changes

- Add a repository-owned synthetic agent coverage matrix for all currently
  modeled FlowPilot AI/action branch families.
- Require every matrix row to declare its model obligation, branch kind,
  evidence owner, trace pack or ordinary test owner, evidence status, and
  whether synthetic evidence is allowed to support only control-flow confidence.
- Extend synthetic trace packs and focused tests for branch families that can
  be replayed through real FlowPilot packet/runtime/evidence APIs.
- Add gating tests so a new model/test branch cannot silently lack coverage
  ownership.
- Close the current FlowGuard full-coverage blockers from deferred structure
  split diagnostics, or leave any unclosed blocker as an explicit failed gate.
- Preserve the boundary that synthetic or fixture traces never prove live AI
  semantic quality, delivered product quality, or live project completion.

## Capabilities

### New Capabilities

- `synthetic-agent-coverage-matrix`: coverage inventory and gates for synthetic
  AI action trace packs, ordinary runtime evidence, background validation
  artifacts, and known non-live evidence boundaries.

### Modified Capabilities

- None.

## Impact

- Affected tests: synthetic agent trace replay tests, model-test alignment
  tests, test-tier gates, and focused runtime contract tests.
- Affected FlowGuard artifacts: model-test alignment JSON, full diagnostic
  coverage evidence, and structure split repair metadata.
- Affected support code: test-only synthetic trace helpers and any required
  compatibility-preserving structure split helpers under the FlowPilot assets
  surface.
- Affected install flow: after validation, synchronize the local installed
  FlowPilot skill and run install audit/checks serially.
