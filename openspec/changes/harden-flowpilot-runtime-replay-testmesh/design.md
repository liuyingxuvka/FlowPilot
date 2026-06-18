## Context

FlowPilot already has these current-contract surfaces:

- `review_window_contracts.py` declares structured Reviewer flow rows and
  generates review-window Cartesian cells.
- `flowpilot_contract_driven_fake_ai.py` generates legal and bad fake-AI
  payloads from packet-local result contracts.
- `flowpilot_contract_exhaustion_mesh_model.py`,
  `flowpilot_cartesian_control_plane_exhaustion_model.py`, and
  `flowpilot_synthetic_agent_coverage_matrix.py` aggregate finite bad-case
  coverage.
- `flowpilot_singleton_identity_model.py` audits live current-run singleton
  authority but currently lacks an explicit powerset-style fixture proving that
  any missing live evidence file stays insufficient.

The missing proof layer is executable runtime replay. A generated cell must not
silently imply that runtime submitted, rejected, reissued, accepted, or
glass-broke it. This change adds a bounded replay model and tests that reuse
the existing fake-AI and review-window rows.

## Goals / Non-Goals

**Goals:**

- Fail orphan or mismatched Reviewer flows as structured contract gaps.
- Prove singleton live evidence completeness over every required-file
  combination.
- Convert selected fake-AI bad payload cells into executable submit/reject/
  reissue/corrected retry/break-glass replay evidence.
- Add a durable real-issue backfeed registry that turns new real-run anomalies
  into fake-AI profiles, contract cells, Cartesian rows, and replay tests.
- Register the new evidence in existing matrix, TestMesh, model-test alignment,
  topology, version, install, and git workflows.

**Non-Goals:**

- Do not prove live AI semantic quality or delivered product quality.
- Do not add legacy aliases, prose parsers, wrapper acceptance, missing-field
  defaults, or historical artifact fallbacks.
- Do not create a new Reviewer authority path or let PM bypass Reviewer
  blockers.
- Do not rewrite the large runtime as part of this test upgrade.

## Decisions

1. **Add a replay model rather than a second runtime.**

   Introduce a small simulation module that models runtime reactions for the
   generated fake-AI cells: `submit_result`, `mechanical_reject`, `reissue`,
   `corrected_second_attempt`, `normal_retry_before_threshold`, and
   `break_glass_threshold`. Tests assert that each required replay cell lands
   on the expected reaction. This keeps the proof executable while avoiding a
   new production state machine.

2. **Bridge generated cells to replay cells explicitly.**

   The replay model consumes existing cell ids from review-window contracts,
   contract-driven fake-AI responder cells, malformed-body profiles, retry
   profiles, and selected projection-gap profiles. Each replay row records
   `source_cell_id`, `replay_suite_id`, `runtime_reaction`, and
   `confidence_boundary`.

3. **Make orphan review flow a hard row gate.**

   Existing `review_window_contract_for_context()` already returns
   `coverage_status = orphan_review_flow`. Add tests and matrix rows that make
   any orphan/missing/mismatched review-window path fail coverage instead of
   remaining a conceptual mutation only.

4. **Use fixture roots for singleton live evidence.**

   Extend singleton identity tests to create temporary current-run roots for
   all 32 presence combinations of the five required evidence files. The only
   full case has all five present and structurally valid; every other case is
   evidence insufficient. Add invalid-content cases for existence-without-valid
   authority.

5. **Backfeed real issues through a registry, not prose notes.**

   Add a data-oriented module with seed rows for the newly discussed real-run
   issue families. Each row names only structured evidence references and
   public field paths. The registry is consumed by contract exhaustion and
   synthetic coverage so a registered issue cannot be "closed" without a
   fake-AI profile, contract cell, Cartesian row, and replay evidence owner.

6. **Keep TestMesh as the parent evidence boundary.**

   Runtime replay suites become child evidence owners. The parent matrix checks
   registration and freshness; it does not inline every payload detail.

## Risks / Trade-offs

- **Replay model could drift from production runtime** -> Keep replay rows tied
  to existing contract cell ids and add focused runtime/unit tests for actual
  helper behavior where possible.
- **Matrix grows too large** -> Limit runtime replay to high-risk selected
  cells while keeping generated coverage for the full finite matrix.
- **False confidence** -> Result artifacts must state that runtime replay is
  non-live control-plane evidence and does not prove live AI semantic quality.
- **Peer-agent edits stale evidence** -> Run focused tests after edits, then
  rerun topology/install/git checks at the end and report any peer changes.
- **Install sync race** -> Run install sync and install audit serially after
  source validation, never in parallel.

## Migration Plan

1. Add OpenSpec artifacts and tasks.
2. Add replay/backfeed model data and generated result artifacts.
3. Add focused tests for review-window orphan gate, singleton evidence
   powerset, replay cells, backfeed registry, TestMesh ownership, and alignment
   boundary text.
4. Run focused unit tests and model runners.
5. Rebuild topology and run install sync/audit/check serially.
6. Bump version/changelog, commit local changes, and keep GitHub push deferred.
