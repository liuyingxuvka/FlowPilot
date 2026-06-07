## Context

FlowPilot is a new-only current-contract runtime. It already attaches
`current_handoff_contract` to packets and rejects missing fields, old wrappers,
and unsupported fallback evidence. The remaining gap is precision: a packet can
say that a branch such as `redesign_route` requires `route_plan`, while the
runtime validator requires a strict nested route-plan schema that is not fully
shown in the branch's packet instructions.

The same class appears in control-plane ergonomics. Runtime must own role reuse
and replacement, but the normal public path currently exposes
`resolve-role-assignment` and `lease-agent` as two visible actions. That is one
runtime authority split into two controller-facing steps. The project should
keep the runtime checks while presenting one current dispatch action.

Status projection has a related issue for staged PM gates. A source packet can
be accepted and still be the source of a pending staged effect, but final
preflight currently reports that accepted packet as a non-current target. That
is a display/projection problem, not a fallback path.

## Goals / Non-Goals

**Goals:**

- Make every current packet family executable from the opened packet and its
  authorized input materials.
- Model and test branch-specific required child shapes, not just top-level
  required fields.
- Keep mechanical checks owned by runtime/router, substantive process checks
  owned by FlowGuard, and human-quality checks owned by Reviewer.
- Collapse normal role dispatch to one visible current-runtime action while
  keeping runtime-owned reuse/replacement/liveness/self-review checks.
- Make staged-gate status projection identify the real next gate instead of
  treating accepted source packets as current-target violations.
- Add fake-AI and historical live-run regression evidence for the observed
  branch-shape and staged-gate projection failures.

**Non-Goals:**

- Do not add compatibility aliases for old FlowPilot packet shapes.
- Do not accept multiple result wrappers for convenience.
- Do not remove runtime role-assignment safety checks.
- Do not make FlowGuard or Reviewer responsible for mechanical field, hash,
  packet-id, or branch-schema validation.
- Do not turn diagnostic commands into alternate user-facing workflows.

## Decisions

1. Extend the packet result contract with branch-specific shape metadata.

   The source-of-truth row remains the packet-result contract family, but it
   gains optional branch shapes keyed by top-level fields such as
   `decision=redesign_route`. The runtime handoff contract and mechanical
   reissue payload use the same branch shape. This avoids a parallel schema
   system and keeps one authority.

2. Make reissue corrections branch-aware.

   A reissued packet should say which branch failed, what field path failed,
   and the smallest legal shape for that same branch. Generic
   `minimal_valid_shape` remains available for the default branch, but it is no
   longer the only correction example for conditional branches.

3. Present one normal role-dispatch action.

   The new public action commits the runtime's current role decision and lease
   in one foreground step. Internally it may call the existing resolution logic
   and use the same role assignment ledger. Existing resolution commands may
   remain diagnostic, but prompts and next-action duty should not teach them as
   a second normal path.

4. Treat staged PM gates as current gate work.

   Final preflight should not report `source_packet_id` as a current-target
   violation when the gate is legitimately waiting for FlowGuard, review,
   system validation, or closure. The projection should name the pending gate
   stage and current packet/result target instead.

5. Use FlowGuard models as the owner of "information is sufficient to act".

   FieldContract accounts fields, ProjectControlInformationFlow models whether
   packet inputs/output/branch/reissue/status are sufficient, and
   Model-Test Alignment binds model obligations to code, prompt, fake-AI, and
   regression evidence.

## Risks / Trade-offs

- Branch metadata can become duplicated if it is hand-written in several
  places. Mitigation: expose it from the packet-result contract table and have
  handoff/reissue builders consume that table.
- Collapsing visible role dispatch could hide useful diagnostics. Mitigation:
  keep diagnostic commands available but remove them from the normal public
  workflow and prompts.
- Existing tests may assert the old visible `resolve_role_assignment` next
  action. Mitigation: update tests to assert one current role-dispatch action
  plus the same underlying ledger evidence.
- Staged-gate preflight changes can accidentally suppress real stale-target
  errors. Mitigation: add negative tests where no staged gate is pending and
  accepted/noncurrent packet targets still fail.

## Migration Plan

1. Add FlowGuard model scenarios and failing tests for branch-shape reissue,
   single visible role dispatch, and staged-gate projection.
2. Implement contract metadata and runtime projection changes.
3. Update prompts/cards to reference the new single dispatch action and branch
   handoff contract.
4. Update fake-AI rehearsals to be contract-blind and branch-aware.
5. Run targeted checks, then broader model/test/install/topology validation.
6. Sync installed FlowPilot assets and commit the complete local version.
