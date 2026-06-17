# Design

## Current Owner Reuse

This change reuses existing owners:

- `packet_result_contracts.py` remains the authoritative packet-result family
  registry.
- `runtime.py` remains the packet generator and mechanical gate owner.
- Runtime cards remain role-facing prompt guidance.
- FieldLifecycleMesh, information-flow alignment, model-test alignment,
  ContractExhaustionMesh, Cartesian coverage, and ordinary tests remain the
  validation surfaces.
- `scripts/check_install.py` remains the public install check entrypoint.

No compatibility surface is introduced. Unknown stage/evidence family lookups
must block during validation instead of falling back to a generic stage.

## Stage/Evidence Matrix

Add a dependency-light module under
`skills/flowpilot/assets/flowpilot_core_runtime/` that maps each packet-result
family to:

- `subject_stage`: the lifecycle stage being judged now;
- `subject_evidence_kind`: the evidence type due at that stage;
- `current_pass_criteria`: what can pass now;
- `not_required_until_stage`: evidence that is future-stage only;
- `forbidden_premature_blockers`: blocker reasons that are invalid at this
  stage;
- `target_workspace_artifacts_required`: whether target-project files must
  exist now;
- `toolchain_evidence_owner`: whether FlowPilot install/runtime evidence comes
  from installed skill self-check receipts or target-project outputs.

The matrix is a clarification layer over current packet contracts, not a new
authority. Packet result validators still enforce required fields. FlowGuard
and Reviewer instructions use the matrix to avoid stage-mismatched blocking.

## Runtime Integration

When Runtime creates a FlowGuard packet for a subject result, it embeds the
stage/evidence matrix row for that subject family. The FlowGuard operator is
instructed to:

1. judge only the current subject packet/result;
2. require the matrix's current-stage evidence;
3. treat `not_required_until_stage` rows as future obligations unless the
   subject claims that evidence has already been produced;
4. keep final direct-evidence gates strict at terminal/replay stages.

For PM high-standard contract results, the current evidence is the requirements
list plus `acceptance_item_registry`. The `required_evidence` text inside
acceptance items is future closure policy, not immediate artifact proof.

## Installed Runtime Self-Check Receipt

FlowPilot should be portable after installation. A target project using the
installed skill should not need the FlowPilot development repository or its
`simulations/run_flowpilot_model_test_alignment_checks.py` script.

Add an installed-skill self-check script that verifies the installed runtime
kit, packet contracts, stage/evidence matrix, and FlowGuard importability from
the installed skill root. Runtime records a run-scoped receipt under the target
project `.flowpilot/runs/<run-id>/` at startup. FlowGuard package examples and
minimal shapes should refer to that receipt, not to a dev-repo simulation path.

## Validation Strategy

Focused validation must prove both sides:

- plan/preplanning packages can pass with correct stage-definition evidence and
  without future result evidence;
- result/terminal packages still block missing direct evidence, stale evidence,
  skipped model checks, and fake-AI package success.

Coverage must include positive and negative rows in unit tests, fake-AI
rehearsal, FieldLifecycleMesh, information-flow alignment, model-test
alignment, ContractExhaustionMesh, Cartesian coverage, install checks, and
local installed skill sync.

## Full Current-Contract Cartesian Coverage

Add a generated current-contract Cartesian matrix above the lower-level
control-plane Cartesian model. The matrix covers the bounded product of:

- flow stage and packet/material family;
- action;
- object state;
- AI return profile;
- timing state;
- blocker/repair state;
- route shape;
- execution source;
- final-claim pressure.

The unrestricted symbolic product is documented but not materialized when it
combines stages and actions no current owner can produce. Every non-materialized
class must have an explicit not-applicable reason.

Every materialized cell must name:

- the expected current-contract reaction;
- the evidence owner;
- an absorbing next action that consumes reject/block/reissue outcomes without
  deadlock;
- whether the cell reuses an existing test.

GlassBreak is not a passing current-contract reaction. Any matrix cell that
expects or allows GlassBreak is a validation failure. Repeated same-root
blockers must be absorbed through structured repair delta requirements,
current-packet reissue, PM disposition, or route redesign rather than by
breaking the control plane.

When a generated cell overlaps an existing test, reuse is allowed only if the
existing test is audited for current-contract markers and for absence of
legacy-positive behavior. Stale tests that still accept aliases, fallback
prose, newest-run fallback, old protocol output, or old-router compatibility
must fail the matrix reuse audit instead of being counted as coverage.
