## Context

`split-heavy-flowguard-model-hierarchy` completed the first safety layer: Meta
and Capability are classified as heavyweight parents, child evidence is
registered, and hierarchy checks reject unsafe partition maps or stale evidence.
That change intentionally did not make `meta_model.py` or
`capability_model.py` thin.

The next migration must change routine validation behavior without destroying
the current release safety net. The repository also has active peer-agent work,
so implementation must use narrow patches, preserve unrelated changes, and
avoid treating progress-only background runs as pass evidence.

## Goals / Non-Goals

**Goals:**

- Make default Meta and Capability validation foreground-friendly by checking
  thin parent evidence instead of expanding the full legacy state graphs.
- Preserve full legacy Meta and Capability graph exploration behind explicit
  forced/full or background regression paths.
- Build a machine-readable parent responsibility ledger so thin parent checks
  know which child model, shared kernel, or parent-only check owns each
  partition and invariant family.
- Add executable hazards that make stale child results, missing proofs, hidden
  skips, uncovered partitions, sibling overlap, and release-confidence
  overclaims fail.
- Keep install/smoke/check surfaces aligned and sync the installed FlowPilot
  skill after repository validation.

**Non-Goals:**

- Do not delete the legacy monolithic model files in the first implementation
  slice.
- Do not claim full release confidence from thin parent checks unless full
  legacy regressions or valid equivalent proof evidence are current.
- Do not change FlowPilot runtime semantics unless a small validation hook is
  required for evidence reporting.
- Do not revert or exclude compatible peer-agent changes.

## Decisions

### Introduce Thin Parent Evidence Checks Before Deleting Legacy Graphs

Default Meta and Capability runners should move to a thin-parent path that
loads child result metadata, proof metadata, partition ownership, and the parent
responsibility ledger. The legacy graph exploration remains available through
an explicit full/forced mode and background log contract.

Rationale: this immediately removes routine long foreground runs while keeping
the old graph as an oracle during migration.

Alternative considered: rewrite `meta_model.py` and `capability_model.py`
directly into small models in one pass. Rejected because the files contain
thousands of lines of accumulated invariants and labels; deleting them before a
ledger and equivalence gate exists would create hidden coverage loss.

### Keep Result Types Separate

Thin parent result/proof artifacts should be distinguishable from legacy full
regression artifacts. Validation may expose both, but a thin result must not
overwrite the only evidence for a full run unless the runner explicitly records
the result type and release-confidence boundary.

Rationale: old consumers already inspect `results.json` and
`capability_results.json`; the migration needs compatibility, but reviewers
must still know whether a result came from thin evidence aggregation or full
legacy graph exploration.

### Treat Child Models as Evidence Contracts

Thin parents should not import or expand child state graphs. They should read
the child artifacts as evidence contracts containing model id, result path,
state/edge count, ok status, proof/freshness status, covered parent
partitions, skipped checks, and release eligibility.

Rationale: the performance win comes from avoiding child graph expansion inside
the parent.

### Migrate by Parent Partition

The first implementation should start with the existing hierarchy partition map
and add a parent responsibility ledger. Each partition moves from "covered by
the full parent graph" to one of:

- child-owned with current evidence;
- shared-kernel owned with current evidence;
- parent-only thin check;
- legacy-full-only obligation;
- explicit out-of-scope with reason.

Rationale: partition-by-partition movement exposes gaps and avoids all-or-none
rewrites.

### Split Recursively by State-Explosion Threshold

The hierarchy is not fixed at two layers. A thin parent should aggregate only
bounded evidence contracts. If any child or shared-kernel model grows past the
heavyweight threshold, that model should become a domain parent with its own
ledger and thinner children. The target validation shape is a sum of small
proof obligations across layers, not a product graph that expands every
ancestor and descendant state together.

Rationale: this keeps routine foreground validation stable as FlowPilot grows,
while preserving explicit full or sampled deep regressions for release
confidence.

### Background Full Regressions Remain Mandatory for Release Claims

Foreground validation should run thin parents, hierarchy, mesh, and focused
child checks. Full Meta/Capability regressions should run in
`tmp/flowguard_background/` for release-level confidence, forced validation, or
when the thin-parent ledger touches a parent-only or legacy-full-only area.

Rationale: the user explicitly wants long regressions in the background while
foreground implementation continues.

## Risks / Trade-offs

- Thin checks may overclaim coverage if the ledger is too coarse -> add
  missing-child, stale-proof, hidden-skip, uncovered-partition, and
  release-overclaim hazards before relying on the path.
- Some old invariants may not map cleanly to child models -> mark them
  parent-only or legacy-full-only until a focused child model exists.
- Existing consumers may assume `results.json` means full graph exploration ->
  include result type, evidence tier, and release-confidence fields, and update
  validation readers.
- Peer agents may modify nearby validation files -> reread touched files before
  each patch and keep final staging inclusive of compatible external work.
- Valid proof reuse can hide missed source changes -> fingerprints must include
  the ledger, thin parent helper, runner, and relevant child evidence inputs.

## Migration Plan

1. Add a parent responsibility ledger for Meta and Capability partitions and
   invariant families.
2. Add a thin parent helper/model that checks child evidence contracts and
   emits explicit release-confidence boundaries.
3. Add or update runner modes so default foreground checks use thin parents and
   explicit full/forced modes preserve legacy graph exploration.
4. Add equivalence and stale-evidence hazards, plus focused tests for default
   thin behavior and forced full behavior.
5. Update hierarchy, mesh, smoke, install, and coverage-sweep surfaces to read
   thin parent evidence without losing full-regression obligations.
6. Launch full Meta/Capability regressions in background using the standard log
   artifact contract, then inspect final exit/meta/result/proof artifacts before
   reporting release-level confidence.
7. Sync the installed FlowPilot skill from the repository and verify source
   freshness.
8. Recheck git status, include compatible peer-agent changes, and commit the
   integrated result when validation is complete.

Rollback: keep the legacy runners and model files intact. If thin parent
checks misbehave, default runners can be switched back to legacy full graph
exploration while preserving the new ledger and hazards for a follow-up fix.

## Open Questions

- Whether the compatibility `results.json` files should be thin-parent results
  by default immediately, or whether thin results should live beside legacy
  files for one transition cycle.
- Which old Meta/Capability invariant families have no focused child owner and
  should remain parent-only or legacy-full-only in the first slice.
