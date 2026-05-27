## Context

FlowPilot actions already carry `next_step_contract` metadata such as target
role, apply/receipt mode, ACK clearance, dispatch-recipient gates, and
controller-user reporting policy. That metadata is currently checked by
ordinary tests, but it is not projected into FlowGuard's
`WorkflowStepContract`, so DevelopmentProcessFlow and Model-Test Alignment
cannot uniformly reject missing prerequisite receipts, stale receipts,
forbidden skips, or claims made before the required step completes.

The current final confidence gate is also blocked because the full
model-test-code diagnostic reports two runtime contract surfaces above the
StructureMesh threshold and one stale legacy-full evidence row. This change
keeps the runtime behavior stable while adding executable step-contract
evidence, reducing the flagged owner modules, and refreshing/superseding the
stale validation evidence.

## Goals / Non-Goals

**Goals:**

- Convert representative FlowPilot `next_step_contract` dictionaries into real
  FlowGuard `WorkflowStepContract` objects.
- Add a focused FlowGuard check runner and ordinary tests for prerequisite,
  receipt, invalidation, skip, and claim-gate behavior.
- Feed workflow-step evidence into the source-audited model-test alignment
  plan and the full diagnostic inventory.
- Clear the current final-confidence blockers without reverting peer work.
- Keep local install sync serialized after source validation.

**Non-Goals:**

- Do not redesign Router action semantics or change public JSON shapes.
- Do not remove the historical legacy-full Meta/Capability commands.
- Do not make broad wrapper Router test modules routine evidence again.
- Do not use documentation-only assertions as final confidence evidence.

## Decisions

1. **Add a projection module instead of changing every action producer.**

   The first implementation will read existing action dictionaries and project
   them into `WorkflowStepContract` instances. This preserves current public
   action payloads while giving FlowGuard a stable contract layer.

2. **Keep contract review separate from Router execution.**

   A new simulation/check runner will construct representative action traces
   and known-bad traces. It will not run the full Router or mutate run state.
   Runtime behavior remains covered by the existing Router tests.

3. **Feed step-contract rows into Model-Test Alignment.**

   Workflow-step contracts become source-audited obligations with matching
   tests. The full diagnostic then sees the step-contract runner as a current
   model/check surface instead of a prose-only process rule.

4. **Use StructureMesh child modules for current runtime over-threshold files.**

   The daemon runtime can be reduced by extracting diagnostics helpers. The
   controller break-glass helper can be reduced by extracting recovery
   supervisor operations and CLI handling while keeping the original module as
   the compatibility facade.

5. **Refresh layered full proof before relying on legacy-full supersession.**

   The legacy monolithic commands remain available, but the stale
   `meta_legacy_full` row may only be reclassified when the current layered
   full proof is valid.

## Risks / Trade-offs

- Step-contract projection can under-model a contract field if the mapping is
  too narrow -> Mitigate with explicit known-bad traces and tests for the
  highest-risk fields first.
- Splitting runtime modules can break facade imports -> Mitigate by preserving
  original function names on the parent modules and running facade/import
  contract tests.
- Background model proofs can be stale after peer edits -> Mitigate by checking
  final artifacts and rerunning the final confidence gate after all source and
  install sync steps.
- The first step-contract pass will not cover every possible action field ->
  Mitigate by making uncovered fields visible as follow-up metadata rather than
  claiming full semantic proof for every internal action branch.
