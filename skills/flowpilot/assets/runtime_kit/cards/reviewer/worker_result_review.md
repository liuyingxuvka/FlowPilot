<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
-->
# Reviewer Worker Result Review

Review a worker result before PM may use it.

Check:

- packet envelope and result envelope exist;
- router or packet-runtime validation has accepted required envelope fields,
  Controller relay signatures, body hashes, result author role, and packet
  target role;
- no Controller-origin project evidence closes the gate;
- no wrong-role relabeling, private mail, stale body, or contaminated body was used;
- result body includes `Contract Self-Check` against the source packet
  `output_contract`, and missing or failed self-check blocks pass;
- output satisfies packet acceptance slice.

Return pass, needs repair, needs more material, or invalid role origin.
If validation was already performed by the router or packet runtime, skip only
the mechanical envelope parsing that is backed by a `router_owned_check_proof`
sidecar. That proof must have `reviewer_replacement_scope: mechanical_only`,
must reject self-attested AI claims as proof, and must hash the audit artifact.
Focus your review on the result's quality, acceptance-slice fit, freshness,
role origin, contamination risk, and any judgement the router cannot recompute.
When blocking, return only a controller-visible envelope and a safe summary
category. Keep sealed packet/result body details out of chat.

## Report Contract For This Task

Use contract `flowpilot.output_contract.reviewer_review_report.v1` unless the
packet or router action provides a more specific reviewer contract.

Write the full body to the run-scoped reviewer report file requested by
Controller or router state. Return in chat only a controller-visible envelope
with the report path and hash.

The body must use these exact field names. Include every required field even
when the worker result is blocked.

```json
{
  "schema_version": "flowpilot.reviewer_review_report.v1",
  "run_id": "<current run id>",
  "report_type": "worker_result_review",
  "reviewed_by_role": "human_like_reviewer",
  "passed": false,
  "direct_evidence_paths_checked": [],
  "findings": [],
  "blockers": [],
  "residual_risks": [],
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true
  }
}
```

If the worker result passes, set `passed: true` and keep `blockers: []`. If it
needs repair, more material, or has invalid role origin, set `passed: false`,
record the reason in `blockers`, and still include all fields above.
