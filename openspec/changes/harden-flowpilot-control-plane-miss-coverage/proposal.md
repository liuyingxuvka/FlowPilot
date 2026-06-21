## Why

Recent live FlowPilot runs exposed model-miss defects after earlier "full coverage"
claims: reviewer self-review was accepted as system validation, route progress
could appear to move backward, formal reviews passed with no PM improvement
suggestions, final-closure blocker combinations fell into break-glass instead
of normal repair, and fake-AI rehearsal did not cover several same-class
contract gaps.

This change closes the gap between declared coverage and live control-plane
behavior by backfeeding the observed misses into stronger Cartesian fake-AI
coverage and by repairing the smallest current-contract runtime/prompt paths.

## What Changes

- Expand fake-AI and model-test coverage from observed examples to full
  same-class matrices for review identity, review report completeness,
  acceptance-item projection, formal attachments, final-closure blockers,
  progress display monotonicity, and break-glass thresholds.
- Tighten current-contract runtime gates so a reviewer replacement cannot reuse
  the same agent, a blocked/self-review review cannot satisfy system
  validation, and formal review reports cannot pass without PM-facing
  improvement suggestions.
- Keep route progress as a monotonic display projection that preserves prior
  setup/formal nodes and appends repair/reopen work instead of replacing the
  visible route denominator.
- Route final-closure blocker combinations through normal PM/runtime repair
  while preserving the existing same-class fifth-repeat break-glass fuse.
- Improve reviewer and controller prompt/card guidance inside existing packet,
  result, review, and break-glass surfaces, without adding compatibility
  aliases, fallback parsers, or parallel authority ledgers.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `synthetic-agent-coverage-matrix`: add full same-class Cartesian fake-AI
  coverage for the newly observed miss families and require evidence ownership
  for each generated cell.
- `flowpilot-control-plane-contract-kernel`: reject same-agent replacement,
  blocked/self-review validation, incomplete contract feedback, and hidden
  current-contract gaps through the existing runtime contract path.
- `formal-gate-review-standards`: require independent reviewer reports to
  include PM-facing higher-standard suggestions while reserving hard blockers
  for unmet minimum requirements, missing evidence, quantitative shortfall, or
  protocol failures.
- `route-display-refresh`: make user-visible progress monotonic and cumulative
  across pre-route work, formal route expansion, repair, and reopened work.
- `controller-break-glass-repair`: ensure break-glass remains a control-plane
  fuse after normal repair paths fail or same-class repeats reach the threshold,
  not the default for final-closure blocker combinations.
- `terminal-ledger`: ensure final closure owns normal repair routing for
  route-wide ledger, terminal replay, node acceptance, and node-context gaps.

## Impact

- Affected runtime/code: FlowPilot core runtime review/lease/validation paths,
  router role-binding payloads, terminal/final-closure repair selection,
  progress display projection, reviewer result contract validation, and
  current prompt/card text.
- Affected models/tests: fake-AI contract-driven rehearsal, runtime replay
  model, control-plane contract/exhaustion models, planning/review quality
  models, router runtime tests, and model-test alignment/TestMesh evidence.
- No new compatibility surface is introduced. Unsupported old or duplicate
  authority paths are rejected or deleted rather than normalized.
