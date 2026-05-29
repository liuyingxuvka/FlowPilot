## Why

The new-only FlowPilot runtime is now active, but several maintenance surfaces still
carry stale compatibility wording, duplicate validation artifacts, no-op alias hooks,
and oversized prompt/test helpers. This cleanup makes the current FlowPilot contract
easier to maintain without reintroducing old workflow paths.

## What Changes

- Remove active OpenSpec wording that still describes old inputs as compatibility
  aliases or safe caller paths.
- Keep negative legacy/retired fixtures only where they prove old inputs are rejected.
- Canonicalize validation evidence around current `*_results.json` artifacts and
  remove stale shadow `*_checks_results.json` artifacts when a current canonical
  artifact exists.
- Remove empty alias hooks and no-op normalization functions that no longer provide
  current behavior.
- Compress long runtime cards only where the same obligations can be stated with
  less duplicated text.
- Split the largest shared test helper surface only where ownership is clear and
  validation coverage remains equivalent.
- Synchronize the installed local FlowPilot skill, run current validations, and commit
  the local git result without pushing, tagging, releasing, or deploying.

## Capabilities

### New Capabilities

- `validation-artifact-canonicalization`: Validation evidence has one canonical
  current result artifact per model/check family, and shadow artifacts cannot carry
  stale compatibility semantics.

### Modified Capabilities

- `flowpilot-new-only-runtime`: current runtime evidence and maintenance files must
  not preserve retired aliases as active accepted paths.
- `executable-repair-transactions`: retired repair kinds such as `event_replay`
  remain rejected, not compatibility-normalized.
- `packet-open-authority-exits`: old reviewer-named relay helpers are not active
  authority paths for PM-bound result access.
- `startup-answer-reconciliation`: startup answers are owned by native intake and
  deterministic seed evidence, not by a legacy answer-recording replay row.
- `startup-settlement-ownership`: startup settlement must not reissue or reconcile
  legacy answer-recording rows as current work.
- `deterministic-startup-bootstrap`: deterministic bootstrap docs must describe the
  current seed-owned answer path without teaching legacy row names.
- `flowpilot-packet-review-flow`: old reviewer-dispatch flags are retired audit
  history, not current evidence for new package review.
- `flowpilot-prompt-boundary-policy`: active prompts/cards stay current-only while
  preserving current fallback safety mechanisms.
- `flowguard-thin-parent-models`: thin-parent evidence selection must prefer
  canonical current result artifacts over stale shadow check artifacts.
- `tiered-flowpilot-test-validation`: validation should detect duplicate/stale result
  artifacts without treating historical duplicates as current proof.

## Impact

- Affected areas include `openspec/specs/`, `simulations/` result selection and
  result artifacts, `scripts/audit_validation_artifacts.py`, FlowPilot runtime card
  markdown, packet/gate helper modules, selected tests, local install scripts, and
  generated validation evidence.
- Current runtime behavior should stay new-only. Existing rejection tests for old
  inputs remain protection, not deletion candidates.
- No historical `.flowpilot/runs` data, backups, releases, tags, pushes, deployments,
  or private account data are in scope.
