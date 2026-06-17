# Design

## Existing Owner Reuse

This change extends existing owners:

- `flowpilot_new_role_commands.py` owns the addressed role's current
  `open-packet` and `submit-result` CLI surface.
- Runtime handoff contracts in `flowpilot_core_runtime/runtime.py` already
  contain the complete packet/result contract projection.
- Role cards and generated payload contract sources own role-facing guidance.
- Field lifecycle currentness and model-test alignment already cover current
  field and prompt-contract obligations.

No new protocol family is introduced.

## Submission Checklist Projection

`open-packet` should keep the Controller/body boundary intact while returning a
role-hidden mechanical checklist. The checklist is derived from:

1. current packet body fields when present;
2. `envelope.current_handoff_contract.required_report_contract` for the
   complete result contract;
3. `envelope.current_handoff_contract.input_material_manifest` for required
   authorized input/result reads.

The checklist is a projection, not a new authority. It must not let Controller
read sealed bodies or authorize sibling packets.

## Prompt Surface Cleanup

Current role-facing guidance must point to:

- `flowpilot_new.py open-packet --lease-id <lease-id> --packet-id <packet-id>`;
- `flowpilot_new.py submit-result --lease-id <lease-id> --packet-id <packet-id>
  --body <sealed_result_summary>`;
- `flowpilot_new.py progress --lease-id <lease-id> --packet-id <packet-id>
  --status <metadata-only-status>` for progress-only metadata.

Lower-level role-output helper commands can remain internal implementation
surfaces, but active role cards and generated role-facing contract text must
not teach them as the live handoff path.

## Field Lifecycle

Behavior-bearing old aliases are rejected, not normalized:

- `reason` must not substitute for `decision_reason`;
- `checked_by_role` must not substitute for `reviewed_by_role`;
- `runtime_open_receipts` must not substitute for
  `runtime_open_receipt_refs`;
- `mode`, `from_role`, `recipient_role`, and `kind` must not substitute for
  current PM request fields.

Each rejection gets focused negative coverage so future cleanups do not
reintroduce compatibility through helper fallback code.

## Validation Strategy

Focused validation comes first:

- unit tests for checklist projection and alias rejection;
- prompt/card coverage tests for obsolete command exposure;
- field contract and model-test alignment checks for field and prompt
  obligations.

Long parent regressions can run through the background artifact contract and
are not completion evidence until stdout, stderr, combined output, exit code,
and metadata artifacts exist.

