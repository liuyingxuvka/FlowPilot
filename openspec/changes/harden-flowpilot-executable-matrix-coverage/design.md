## Context

FlowPilot currently has several coverage layers: model-local Cartesian matrices,
synthetic agent coverage, fake project rehearsals, real Router dry-run
rehearsals, TestMesh/tiered validation, and Controller break-glass policy. The
recent current-contract Cartesian matrix is useful, but it is a model and
oracle layer. It proves that a declared class should accept, reject, reissue,
block, repair, redesign, stop, or enter break-glass; it does not prove that a
prepared fake AI body can be opened through a current packet, submitted through
the public Runtime/CLI, recorded in event logs, and converge without stale
evidence or hidden old results.

Recent fake project debug evidence showed concrete failures below the model
layer, including repeated mechanical blocks for missing `current_evidence_refs`,
packet body shape drift, terminal replay field drift, terminal supplemental
repair lineage gaps, public CLI worker lifecycle sensitivity, and stale result
artifacts that still reported green. This change turns those misses into a
first-class executable coverage bridge.

## Goals / Non-Goals

**Goals:**

- Keep the model-local matrix, but make its high-risk cells produce executable
  coverage targets.
- Add a bridge model/checker that records, for each required bridge row, the
  model cell id, fake body generator, Runtime/CLI entrypoints, event-log
  evidence, convergence rule, break-glass expectation, and freshness receipt.
- Separate five evidence levels: model-only, fake-body contract, Runtime/CLI
  replay, long-chain convergence, and fresh parent-confidence evidence.
- Encode the break-glass rule precisely: known recoverable paths must not enter
  break-glass, but the fifth same-class no-progress repeat must enter
  Controller break-glass as a safety fuse.
- Feed bridge case ids and shards into TestMesh, Model-Test Alignment, coverage
  inventory, and install checks so broad confidence cannot rely on model-only
  evidence.
- Preserve peer-agent work and the current contract-reduction change by adding
  a focused bridge instead of widening packet contracts or adding compatibility
  paths.

**Non-Goals:**

- Do not introduce live AI semantic testing in this change.
- Do not treat fake AI packages as proof of delivered product quality or live
  AI quality.
- Do not add compatibility for old aliases or wrappers. Legacy and old-field
  cases remain negative tests.
- Do not rewrite the existing `reduce-flowpilot-contract-surface` change.
- Do not replace existing fake project rehearsals; consume and sharpen them.

## Decisions

1. Add a separate executable bridge model instead of expanding the current
   Cartesian model.

   Rationale: the current matrix owns model-local decision coverage. Executable
   replay coverage has different evidence: body generation, CLI command
   receipts, event logs, convergence limits, and result freshness. Keeping a
   separate bridge prevents a model-only pass from being mistaken for Runtime
   proof.

   Alternative considered: add executable fields directly to
   `flowpilot_current_contract_cartesian_matrix.py`. This would make one model
   too thick and blur model-local coverage with runtime evidence.

2. Make bridge rows explicit, not inferred from test names.

   A bridge row must name a `bridge_case_id`, `model_cell_id` or coverage shard,
   packet family, fake body class, public runtime entrypoints, expected outcome,
   convergence expectation, break-glass expectation, evidence command, and
   freshness source. Tests may be reused only when they can cite the bridge row.

3. Use prepared fake AI bodies as executable fixtures, not live semantic proof.

   Prepared bodies are the right tool for deterministic replay of bad packages,
   old fields, wrong roles, stale evidence, and repeated repair loops. They
   still cannot prove live AI quality. Reports must keep that boundary visible.

4. Treat break-glass as a safety fuse, not a normal success path.

   Normal known paths should resolve by reject, reissue, block, repair,
   redesign, terminal stop, or completion. A bridge row may expect break-glass
   only when it intentionally drives the same class without progress to the
   configured fifth repeat threshold.

5. Require freshness receipts for parent confidence.

   A JSON result artifact is not current evidence by itself. Parent coverage,
   topology, install, or final confidence must consume a receipt that binds the
   result path to current source/test inputs, command identity, status, and
   fingerprint. Stale receipts keep broad confidence scoped or blocked.

6. Use TestMesh for the child-suite ownership layer.

   The bridge will produce required child ids. TestMesh owns whether each child
   suite has current passing evidence. Model-Test Alignment owns whether the
   bridge obligation, code contract, and test evidence bind the same behavior.

## Risks / Trade-offs

- [Risk] The bridge can become another large matrix that is slow to run.
  -> Mitigation: keep routine rows focused on high-risk executable cells, and
  report release-only rows separately through TestMesh.

- [Risk] Reusing existing fake project rehearsals can hide stale or weak
  evidence.
  -> Mitigation: require each reused test to cite bridge ids and result
  freshness receipts, not only marker strings.

- [Risk] Parallel agents may continue editing runtime contracts while this work
  is in progress.
  -> Mitigation: prefer independent model/test files and registry rows; rerun
  freshness checks after edits; do not revert peer changes.

- [Risk] Break-glass rows can be misread as normal repaired paths.
  -> Mitigation: bridge rows must classify `break_glass_expected` as
  `forbidden`, `required_at_fifth_repeat`, or `not_applicable`, and reports
  must separate safety-fuse pass from ordinary recovery pass.

- [Risk] A focused bridge may not cover every future live AI surprise.
  -> Mitigation: any future real break-glass or model miss becomes a seed for
  ContractExhaustionMesh and a new bridge row before broad confidence is
  restored.

## Migration Plan

1. Add the OpenSpec specs and implementation tasks.
2. Add the bridge model/checker and result artifact.
3. Add focused tests proving bridge row completeness, break-glass threshold
   semantics, fake body binding, Runtime/CLI evidence binding, and stale result
   detection.
4. Connect bridge summaries to the coverage inventory and model-test alignment
   evidence rows.
5. Rerun focused checks, rebuild topology, sync local installed skill, and run
   install audits.

Rollback is straightforward because the bridge is additive: remove the new
bridge model, tests, result artifact, and inventory references. It does not add
legacy compatibility paths or change the frozen current contract by itself.

## Open Questions

- Which bridge rows should be routine versus release-only after the first full
  implementation pass?
- Should the full fake project public CLI rehearsal remain one parent command
  or be split immediately into TestMesh child suites?
