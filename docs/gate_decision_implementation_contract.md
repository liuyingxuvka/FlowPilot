# FlowPilot GateDecision Implementation Contract

Date: 2026-05-07

## Scope

This contract applies only after a formal FlowPilot run has already started.
It does not define or change FlowPilot invocation rules.

The goal is to make gate decisions explicit enough for existing FlowGuard
models to check prompt delivery, router mechanics, reviewer scope, repair
classification, resource disposition, and state refresh without turning the
router into a semantic reviewer.

## Minimal Contract

Every PM, reviewer, or FlowGuard officer gate decision that can pass, block,
waive, skip, repair, mutate, or affect completion must emit a `GateDecision`
record.

Required fields:

```json
{
  "gate_decision_version": "flowpilot.gate_decision.v1",
  "gate_id": "string",
  "gate_kind": "quality | repair | parent_replay | resource | stage_advance | completion | other",
  "owner_role": "project_manager | human_like_reviewer | process_flowguard_officer | product_flowguard_officer",
  "risk_type": "product_state | visual_quality | mixed_product_visual | documentation_only | composition | resource | control_state | none",
  "gate_strength": "hard | soft | advisory | skip_with_reason",
  "decision": "pass | block | waive | skip | repair_local | mutate_route",
  "blocking": true,
  "required_evidence": ["string"],
  "evidence_refs": [
    {
      "kind": "file | command | screenshot | model_result | reviewer_walkthrough | state_ref | none",
      "path": "string",
      "hash": "string",
      "summary": "string"
    }
  ],
  "reason": "string",
  "next_action": "continue | local_repair | route_mutation | collect_evidence | reviewer_recheck | stop",
  "contract_self_check": {
    "all_required_fields_present": true,
    "exact_field_names_used": true
  }
}
```

`reason` is required for every decision. It is especially important for
`waive`, `skip`, `soft`, and `advisory` decisions because those are the places
where silent AI omission would otherwise look like progress.

## Role Boundaries

Router responsibility is mechanical conformance:

- required fields are present;
- enum values are valid;
- `blocking` matches `gate_strength` and `decision`;
- evidence references have the required path/hash shape when evidence is not
  `none`;
- `next_action` is routeable;
- stage advancement does not occur unless frontier, display, ledger, and
  blocker index refresh together.

Reviewer and PM responsibility is semantic sufficiency:

- `risk_type` fits the real issue;
- the proof method fits the risk type;
- hard gates have a real risk reduction reason;
- visual quality gates include reviewer walkthrough evidence;
- product/state/workflow gates include Product FlowGuard evidence where needed;
- documentation-only gates are not forced through Product FlowGuard;
- local defects remain local;
- route-invalidating findings mutate the route and invalidate stale evidence;
- low-composition-risk parent replay can be waived with a reason;
- delivery evidence is resolved before completion;
- diagnostic temporary resources do not block completion.

The router must not pass or fail a gate because it agrees or disagrees with the
PM or reviewer judgement. It can only reject malformed, unroutable, or
mechanically contradictory records.

## Quality Risk Rules

| Risk type | Required proof path |
| --- | --- |
| `product_state` | Product FlowGuard result |
| `visual_quality` | Reviewer-owned walkthrough |
| `mixed_product_visual` | Product FlowGuard result and reviewer-owned walkthrough |
| `documentation_only` | Light review, or `skip_with_reason` with a concrete reason |
| `none` | `skip_with_reason` with a concrete reason |

FlowGuard verifies that the correct proof path was selected. It does not prove
visual taste or product judgement by itself.

## Repair Rules

| Issue type | Decision | Evidence obligation |
| --- | --- | --- |
| Local defect | `repair_local` | same reviewer recheck after local repair |
| Route-invalidating finding | `mutate_route` | new route version and stale-evidence invalidation |
| Unclear | `block` | PM or reviewer classification before repair proceeds |

## Parent Replay Rules

Parent replay is risk based:

- high composition risk: hard parent replay;
- low composition risk: soft/advisory or waived with a reason;
- no composition risk: skipped with a reason.

The mere presence of child nodes is not enough to make parent replay a hard
blocker.

## Resource Rules

| Resource scope | Completion behavior |
| --- | --- |
| `diagnostic_temp` | nonblocking, record or clean up |
| `delivery_evidence` | must be resolved before completion |
| `advisory_record` | nonblocking |

## Stage Advance Rule

Stage advancement is a single atomic operation from the perspective of
FlowPilot state:

```text
advance_stage -> refresh(frontier, display, ledger, blocker_index)
```

FlowGuard treats split refresh as invalid because it creates stale visible
authority for later roles.

## Existing Model Mapping

Prompt/card instruction models should check that relevant PM, reviewer, and
FlowGuard officer cards tell the role to emit `GateDecision` fields and explain
the meaning of each field.

Router/protocol models should check only mechanical conformance: required
fields, allowed enum values, evidence reference shape, path/hash availability,
blocking compatibility, routeable next action, and atomic state refresh.
Runtime recording uses event `role_records_gate_decision` and contract
`flowpilot.output_contract.gate_decision.v1`.

Reviewer/router scope models should check that semantic sufficiency remains
owned by PM, reviewer, and FlowGuard officers, while the router stays limited
to mechanical validation.

Control-plane models should check that accepted gate decisions are registered
in router-visible state, final gate ledgers, and refreshed display/frontier
views when they affect route progress or completion.

## Minimal Implementation Order

1. Add the `GateDecision` output contract to the contract registry.
2. Add card instructions for PM, reviewer, process FlowGuard officer, and
   product FlowGuard officer to emit the required fields.
3. Add router mechanical validation for the required fields and enum values.
4. Add reviewer/PM semantic checks for proof-method selection and repair
   classification.
5. Register accepted gate decisions into the final gate ledger and any
   route-visible blocker index they affect.
6. Harden stage advance as an atomic refresh operation.

This order keeps runtime changes small. It lets the existing prompt, router,
reviewer-scope, and control-plane models verify the plan before broader
FlowPilot behavior changes are made.
