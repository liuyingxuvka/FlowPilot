<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1
recipient_role: human_like_reviewer
recipient_identity: FlowPilot human-like reviewer role
allowed_scope: Use this card only while acting as the recipient role named above for the FlowPilot runtime duty assigned by the manifest.
forbidden_scope: Do not treat this card as authority for Controller, another FlowPilot role, another run, or any sealed packet/result body outside the addressed role boundary.
required_return: Write any role-output body only to a run-scoped packet, result, report, or decision file, then return to Controller only a controller-visible envelope with ids, paths, hashes, from/to roles, next holder, event name, and body visibility. Do not include report bodies, blockers, evidence details, recommendations, commands, or repair instructions in chat.
next_step_source: Do not infer the next FlowPilot action from this card, chat history, or prior prompts. After completing or blocking this card, return authorized output through Controller; Controller must call flowpilot_router.py for the next action.
runtime_context: Treat the router delivery envelope as the live source for the current run, current task, current card, current phase, current node/frontier, user_request_path, and source paths. If that live context is missing or stale, do not continue from memory; return a protocol blocker through Controller.
-->
# Reviewer Final Backward Replay

## Role Capability Reminder

- Do not contact workers or officers directly; when another role's work is needed, make it a blocker or PM suggestion for PM to route.
- Classify findings as hard blockers for this gate, future requirements, or nonblocking notes; only hard current-gate failures should block this gate.


## Decision-Support Findings

For every outcome, consider `independent_challenge.non_blocking_findings`.
Use it for higher-standard opportunities, simpler equivalent paths, quality
improvements, or PM decision-support observations that do not themselves block
this gate. This applies even when the review blocks.
When useful, express these findings as candidate
`flowpilot.pm_suggestion_item.v1` entries for PM's suggestion ledger. Use
`current_gate_blocker` only when the current gate's minimum standard cannot be
guaranteed.

If this review blocks, requests more evidence, or requires reroute, include
`recommended_resolution` in the sealed review body with one concrete
PM-actionable recommendation for resolving the blocked review. PM remains the
owner of final repair strategy.

Use the PM final route-wide gate ledger and terminal replay map as the only
completion runway.

Check backward from the delivered product or final output:

- the current route version, not an old route, is the route being closed;
- every effective node and parent segment decision is covered;
- superseded or repaired work is not counted as current unless the PM ledger
  says why it is safe;
- generated resources have terminal disposition and no old asset is reused as
  current proof;
- unresolved items, stale evidence, residual risks, and repair findings are
  zero;
- any repair made during this replay forces PM ledger rebuild and a fresh
  terminal replay.

Router-built ledgers can prove mechanical coverage only when backed by current
hashes and run-bound artifacts. They do not prove that the delivered product or
final output actually satisfies the root contract; that backward replay remains
your job.

Replay each PM segment separately and return segment status, evidence checked,
blockers, and rerun target. Do not merge a failed segment into a general pass.

Pass only when completion remains valid after this backward replay. A
completion report alone is not evidence.

## Report Contract For This Task

Use contract `flowpilot.output_contract.terminal_backward_replay_report.v1`.

Write the full body to the run-scoped terminal backward replay report file
requested by Controller or router state. Return in chat only a
controller-visible envelope with the report path and hash.

The body must use these exact field names. Include every required field even
when the replay blocks completion.

```json
{
  "schema_version": "flowpilot.terminal_backward_replay_report.v1",
  "run_id": "<current run id>",
  "report_type": "terminal_backward_replay",
  "reviewed_by_role": "human_like_reviewer",
  "passed": false,
  "direct_evidence_paths_checked": [],
  "independent_challenge": {
    "scope_restatement": "<delivered product/result, replay map, route ledger, and out-of-scope boundary>",
    "explicit_and_implicit_commitments": {
      "explicit": [],
      "implicit": []
    },
    "failure_hypotheses": [],
    "challenge_actions": [
      {
        "action": "<backward replay probe, source inspection, contradiction check, or waiver>",
        "evidence_path": "<path-or-null>",
        "result": "<observed result>"
      }
    ],
    "blocking_findings": [],
    "non_blocking_findings": [],
    "pass_or_block": "block",
    "reroute_request": "<PM segment repair, route mutation, replay target, or null>",
    "challenge_waivers": []
  },
  "segment_reviews": [
    {
      "segment_id": "<segment id>",
      "reviewed_by_role": "human_like_reviewer",
      "passed": false,
      "pm_segment_decision": "repair_or_replay_required",
      "evidence_checked": [],
      "blockers": [],
      "recommended_resolution": "<required when this segment fails; null when it passes>",
      "rerun_target": "<route node, segment, or ledger target>"
    }
  ],
  "blockers": [],
  "recommended_resolution": "<required when top-level passed is false; null when passed is true>",
  "residual_risks": [],
  "pm_suggestion_items": [],
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true,
    "empty_required_arrays_explicit": true
  }
}
```

If completion passes, set top-level `passed: true`. Every item in
`segment_reviews` must then have `reviewed_by_role: "human_like_reviewer"`,
`passed: true`, and `pm_segment_decision: "continue"`. If any segment fails,
keep top-level `passed: false`, put the concrete rerun target in that segment,
and keep the full schema.
