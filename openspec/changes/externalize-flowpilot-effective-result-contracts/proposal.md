# Externalize FlowPilot Effective Result Contracts

## Why

FlowPilot currently exposes base packet-family contracts through
`output_contract`, `current_handoff_contract`, and `submission_checklist`.
Some packet-specific required fields, such as blocker-bound FlowGuard
`semantic_recheck`, are still triggered by packet body contracts. Runtime can
reject missing or malformed fields, but the first packet and the mechanical
reissue packet do not always expose the complete field names, allowed values,
types, and minimal JSON shape in the external contract surfaces.

That makes the path mechanically strict but not reliably digestible for the
role AI: the first attempt can miss a required conditional field, and the
second attempt can move toward the right meaning while using near-alias fields
or wrong value types.

## What Changes

- Add explicit current-result contract profiles to the existing packet result
  contract machinery.
- Runtime will attach profile ids to packet envelopes when a packet requires
  additional mechanical result fields.
- `output_contract`, `current_handoff_contract.required_report_contract`,
  `submission_checklist.result_skeleton`, and reissue packets will use the
  effective contract: base family contract plus explicit profile contract.
- FlowGuard blocker-bound semantic recheck and subject-artifact consumption
  become externally visible result contract requirements instead of body-only
  instructions.
- Reissue packets will carry complete effective minimal shapes, allowed values,
  field type requirements, and forbidden near-alias guidance.
- Prompt/card language will point roles to the external contract surfaces
  rather than treating packet body text as mechanical contract authority.

## Non-Goals

- Do not add fallback alias translation.
- Do not accept old or near-synonym field names as valid current results.
- Do not create a new packet kind, role, ledger, or parallel candidate system.
- Do not move FlowGuard model details back into result bodies.
