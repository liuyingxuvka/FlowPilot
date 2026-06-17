# Design

## Current Baseline

FlowPilot already has the right ownership split:

- `packet_stage_evidence_matrix.py` owns packet-family field lifecycle,
  allowed values, blocker classes, and repair contracts.
- `packet_result_contracts.py` owns result-family shapes.
- Runtime writes `output_contract`, `current_handoff_contract`, and
  `submission_checklist`.
- Runtime reissues the same current packet family after mechanical contract
  failure.

This change extends those surfaces rather than creating a separate protocol.

## Effective Result Contract

Every packet result has an effective contract:

`base family contract + explicit result_contract_profile_ids`

The profile ids live in the packet envelope and output contract. They are not
inferred by scanning packet body prose. Packet body text may explain the work,
but mechanical field authority lives in the external contract surfaces.

Initial profiles:

- `flowguard.semantic_recheck_required`
- `flowguard.subject_artifacts_consumed_required`

Each profile can add:

- required top-level fields;
- required child fields;
- explicit and non-empty array fields;
- allowed value options;
- minimal valid shape entries;
- field type requirements;
- unsupported-field guards used only inside validation and negative tests.

## Runtime Flow

1. Runtime decides the packet's explicit result contract profiles when issuing
   the packet.
2. `issue_task_packet()` writes the profile ids to the envelope and
   `output_contract`.
3. `_build_current_handoff_contract()` builds the effective report contract
   from the envelope profile ids.
4. `open-packet` exposes the effective `submission_checklist.result_skeleton`.
5. `submit-result` validates against the effective contract.
6. Mechanical reissue copies the same profile ids and emits the same effective
   minimal shape plus repair guidance.

## Field Ownership

`semantic_recheck_contract` may remain in the FlowGuard packet body as modeling
context, but it is no longer the only place that tells the AI which result
fields are required. The corresponding result requirement is represented by
`flowguard.semantic_recheck_required` in the envelope contract.

`required_subject_artifacts` may remain in the body as subject context, while
`flowguard.subject_artifacts_consumed_required` represents the result field
requirement externally.

Role-visible packet surfaces use a filtered stage-evidence view. The full
field-lifecycle matrix may keep internal negative-test evidence, but
`current_handoff_contract`, FlowGuard packets, review packets, role cards, and
open-packet checklists expose only current required fields, finite value
options, allowed blocker classes, repair routes, type requirements, and
minimal shapes.

## Reissue Digestibility

Reissue packets must answer three questions without requiring the role to infer
from old prose:

- Which canonical fields must be present?
- What type and value must each mechanically fixed field use?
- Which fields in the submitted result were actually outside the current
  contract, if any?

Runtime must not publish unsupported-field example catalogs to roles. No
unsupported field name is translated into a passing field.
