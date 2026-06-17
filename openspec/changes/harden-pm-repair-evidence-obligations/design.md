## Context

FlowPilot already routes semantic blockers through the current blocker repair
path: active blocker, PM repair decision packet, PM decision result, fresh
repair work, FlowGuard recheck, Reviewer recheck, and blocker clearance. The
current runtime blocks unsupported old fields and has strong FlowGuard
`semantic_recheck` handling, but a PM repair decision for non-terminal
`repair_current_scope` can still be mechanically valid with only `decision` and
`reason`.

The observed failure class is an information-flow field lifecycle miss. The
blocker knows which evidence is missing, but those missing evidence items are
not guaranteed to appear as structured obligations in the PM packet or to be
consumed by the PM result and downstream rechecks.

It is also a sealed-body lifecycle miss. The current control plane already has
sealed packet bodies, sealed result bodies, and authorized result read receipts,
but the repair/recheck model must require downstream roles to read all
runtime-delivered blocker, target, and upstream bodies instead of acting from a
summary or a single latest body.

## Goals / Non-Goals

**Goals:**

- Keep the existing blocker repair path and make the missing evidence items a
  current-contract field lifecycle.
- Derive repair evidence obligations from current blocker data rather than
  free-form prompt text.
- Require PM to disposition every obligation before runtime opens the next
  repair path.
- Reject reason-only, summary-only, registry-only, stale, duplicate, and
  unknown-obligation PM repair outputs mechanically.
- Require every required authorized result/report body to have a concrete
  downstream reader and an open receipt before that role can submit a result.
- Carry all related blocker, target, and upstream result bodies into PM repair,
  repair-worker, FlowGuard recheck, and Reviewer recheck packets through the
  existing `authorized_result_reads` and `current_handoff_contract` path.
- Bind the new obligation fields to FieldLifecycleMesh, ContractExhaustionMesh,
  Model-Test Alignment, TestMesh, synthetic/fake AI coverage, and focused
  runtime tests.

**Non-Goals:**

- No compatibility aliases, legacy field translation, prose guessing, fallback
  parsers, or missing-field defaults.
- No new packet kind, new role, or parallel repair ledger.
- No PM authority to mark FlowGuard, Reviewer, system validation, or worker
  deliverables as passed by explanation text.
- No release or remote publish action.

## Decisions

1. **Use packet-local obligations instead of a new global ledger.**

   The runtime already owns active blockers, packet bodies, result bodies, and
   packet outcomes. The repair evidence obligation list belongs in the existing
   PM repair packet body, and the PM disposition belongs in the existing PM
   repair result body. This avoids a second authority surface.

2. **Name the fields as `repair_evidence_obligations` and
   `repair_obligation_disposition`.**

   `repair_evidence_obligations` is produced by runtime from the blocker.
   `repair_obligation_disposition` is produced by PM. The names avoid implying
   that evidence already exists; they describe what must be repaired and how PM
   routes it.

3. **Derive obligations from current blocker fields.**

   Runtime maps `missing_required_fields`, `stale_evidence_ids`,
   `recommended_resolution`, `blocker_class`, `gate_kind`, and
   `required_recheck_role` into finite obligation rows. Known semantic evidence
   needs include direct deliverable evidence, final replay, ordinary validation,
   formal FlowGuard evidence, matching FlowGuard report handoff, route/node
   context, and explicit waiver authority.

4. **Validate PM disposition before applying the PM decision.**

   The existing `_pm_repair_decision_result_violation` contract remains the
   single mechanical gate. When a PM packet declares obligations, the result
   must cover each obligation exactly once. A disposition cannot claim the
   obligation is satisfied by `reason`, `summary`, or acceptance-registry text.

5. **Model the lifecycle in existing FlowGuard routes.**

   FieldLifecycleMesh records the field chain. ContractExhaustionMesh and the
   Cartesian control-plane model generate missing/empty/wrong/old/stale
   obligation cases. Model-Test Alignment binds obligations to owner code
   contracts and tests. TestMesh and synthetic coverage own broad and fake-AI
   evidence visibility.

6. **Use the existing authorized-result-read bridge for sealed body
   consumption.**

   Runtime already owns packet open, sealed body delivery, result body hashes,
   and open receipts. Repair and recheck packets should therefore receive all
   related bodies through `authorized_result_reads`, and
   `_required_authorized_result_read_blockers` remains the single submit-time
   gate for missing body reads. This avoids a second mail-reading path.

## Risks / Trade-offs

- **Risk:** The new field becomes another verbose prompt-only item.
  **Mitigation:** Runtime validation rejects PM results that do not cover packet
  obligations, and model/test alignment binds the field to code contracts and
  tests.

- **Risk:** The obligation list grows too broad.
  **Mitigation:** Generate only blocker-derived obligations and keep arbitrary
  future semantic analysis out of scope. Unknown source fields remain advisory
  unless mapped to a finite obligation kind.

- **Risk:** Existing terminal supplemental repair branch conflicts with the new
  disposition field.
  **Mitigation:** Keep terminal supplemental requirements unchanged; add
  obligation disposition as an additional requirement when obligations exist.

- **Risk:** A role sees one helpful body and skips another related body.
  **Mitigation:** Runtime marks related bodies `required_before_submit`, records
  open receipts for each body, and role cards/handoff text now require reading
  every delivered blocker, target, and upstream body.

- **Risk:** Parallel agents changed nearby runtime repair behavior.
  **Mitigation:** Read and preserve the current worktree first, then make
  additive current-contract edits without reverting existing changes.
