## Context

The previous route-gate change intentionally removed ordinary
`node_prework_flowguard`. The ordinary node path is now:

1. PM self-checks the active node.
2. PM submits `task.node_acceptance_plan` with a current
   `node_context_package`, or submits `redesign_route`.
3. Reviewer reviews the PM node plan before Worker dispatch.
4. Worker executes the accepted leaf node.
5. FlowGuard checks the Worker result.
6. Reviewer independently reviews the Worker result.

The live failure shows that the model treated both Reviewer stages as generic
"Reviewer passed" booleans. That was too coarse: the first Reviewer stage owns
plan quality, while the second owns completed-result quality.

## Goals

- Preserve the current single trunk and current repair packets.
- Make the review subject determine the evidence standard.
- Keep PM as node/route-plan owner and Reviewer as the independent gate.
- Keep Worker artifacts mandatory at Worker-result review, not at PM
  node-plan review.
- Keep old `node_prework_flowguard` unsupported.

## Non-Goals

- Do not add a compatibility or migration path for old FlowPilot packets.
- Do not add a new role, ledger, packet family, or fallback parser.
- Do not lower Worker-result evidence standards.
- Do not let Reviewer write the PM route or node plan.

## Design

1. **Model the two Reviewer stages separately.**

   The current-node trunk model should distinguish:

   - `node_plan_reviewer_packet_issued` /
     `node_plan_reviewer_used_plan_stage_standard`; and
   - `final_reviewer_packet_issued` /
     `final_reviewer_used_result_stage_standard`.

   A safe ordinary path reaches Worker only after the plan-stage Reviewer
   checks PM node plan quality. It reaches node completion only after the
   result-stage Reviewer checks Worker artifacts and post-result FlowGuard.

2. **Add same-class bad cases.**

   The model and runner should fail when:

   - Reviewer requires Worker artifacts during PM `node_acceptance_plan`
     review.
   - Reviewer accepts PM node-plan review as if it were Worker-result proof.
   - Reviewer accepts a Worker result before post-result FlowGuard.
   - Reviewer accepts a Worker result without current artifact/evidence
     inspection.

3. **Use existing packet context.**

   Runtime already knows `packet_kind`, `route_scope`,
   `current_handoff_contract.contract_family_id`, `staged_effect`, and
   `flowguard_evidence_manifest`. The repair should derive review-stage
   guidance from those current fields instead of adding a new persistent field.

4. **Prompt only the existing roles.**

   Reviewer guidance should state that ordinary `node_acceptance_plan` review
   checks whether the PM plan is executable, sufficiently deep, and safe to
   hand to Worker. Missing Worker artifacts are not a blocker at this stage.

   Worker-result review remains strict: missing artifacts, missing direct
   evidence, missing fresh checker output, stale evidence, or missing
   post-result FlowGuard can still block.

5. **Validation follows the model miss.**

   Verification must first show the model catches the observed bad class, then
   show runtime/cards/fake-AI behavior follows the model.

## Validation

- OpenSpec strict validation for this change.
- FlowGuard current-node route-gate model check.
- Model-test-alignment check after model/test/prompt changes.
- Focused runtime tests for node-plan review packet guidance and Worker-result
  review standards.
- Fake-AI/card coverage tests for the two review-stage standards.
- Topology rebuild/check if model, runner, prompt, or test registries change.
- Installed skill sync and local install audits.
