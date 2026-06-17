## Context

The current FlowPilot runtime already has strong current-contract checks for normal packet creation, PM repair packets, FlowGuard semantic rechecks, Reviewer handoffs, and submit-time required-body open receipts. The recent live WorldGuard run showed that those checks did not fully cover a derived transition: when a FlowGuard check result was mechanically rejected and runtime generated a current-contract reissue packet, the new packet preserved important body payload context but did not pass the source packet's `authorized_result_reads` into `issue_task_packet`. As a result, the fresh packet's envelope and `current_handoff_contract` had `required_authorized_read_count: 0` even though the subject/target result was still required.

This is a model miss, not a novel AI-output typo. The old coverage exhausted fields within declared packet families, but it did not declare the transition invariant that derived packets must inherit material-read obligations from their source packet when the subject, target result, blocker, and packet kind remain bound.

## Goals / Non-Goals

**Goals:**

- Add a derived material lifecycle boundary to the existing FlowGuard model network.
- Make FlowGuard current-contract reissue packets inherit required authorized result reads at the envelope and handoff-contract layer.
- Generate same-class bad cases for lost inherited reads, read ids, read count, semantic recheck contract, repair obligations, blocker identity, and evidence policy.
- Add observed-regression and same-class tests that fail if a derived reissue packet loses required material reads.
- Keep the existing current-contract packet/result surfaces and current repair path.

**Non-Goals:**

- No new packet kind, new repair ledger, or parallel candidate system.
- No compatibility shim, old field alias, old-shape translation, fallback prose parser, or missing-field default.
- No claim that arbitrary natural-language behavior is exhausted; the claim is limited to declared finite current-contract derived-packet material inheritance boundaries.

## Decisions

1. **Model derived packet inheritance as a transition, not as a field list.**
   - Rationale: The failing case had many fields present in the reissue body, but the envelope-level required read list was lost. Field-local checks cannot prove source-to-derived equality.
   - Alternative rejected: Add another standalone field check for `authorized_result_reads`; that would still miss future source/new-packet equality breaks.

2. **Use `issue_task_packet(..., authorized_result_reads=...)` as the single commit point.**
   - Rationale: `issue_task_packet` already projects authorized reads into the envelope, the body, and `current_handoff_contract`, and submit-result already enforces open receipts.
   - Alternative rejected: Patch only `_flowguard_reissue_inherited_body_payload`; body payload text is not runtime enforcement.

3. **Extend existing FlowGuard routes instead of adding a new framework.**
   - Rationale: FieldLifecycleMesh owns behavior-bearing field lifecycle, ContractExhaustionMesh owns canonical bad cases, Cartesian owns model-scoped combinations, Model-Test Alignment owns model/code/test binding, and TestMesh owns broad evidence freshness.
   - Alternative rejected: A separate reissue audit runner unconnected to the model network would repeat the same coverage drift risk.

4. **Treat the observed WorldGuard path as a required replay-style regression.**
   - Rationale: This specific path is the proof that previous green checks overclaimed. The regression must simulate a FlowGuard check result blocked by missing `semantic_recheck`, then verify the generated reissue packet inherits required reads and blocks submit until opened.
   - Alternative rejected: Only testing the helper that copies reads would not prove end-to-end runtime behavior.

## Risks / Trade-offs

- **Risk: More generated cases can make reports look larger.** -> Keep the new boundary model-scoped and finite: source packet has required reads vs none; reissue same subject/target vs no target; retained vs lost inheritance fields.
- **Risk: A derived packet with no prior material may be falsely blocked.** -> Allow zero required reads only when the source packet also has no required reads or the transition records an explicit current-contract no-material reason.
- **Risk: Existing model evidence becomes stale after model/test edits.** -> Rerun FieldLifecycleMesh, ContractExhaustionMesh, Cartesian, Model-Test Alignment, synthetic coverage, topology, and relevant runtime tests before claiming completion.
- **Risk: Parallel agents may be editing adjacent files.** -> Keep edits scoped and do not revert unrelated dirty files.
