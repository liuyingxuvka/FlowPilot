## Why

PM repair packets now correctly require `repair_obligation_disposition` when
they declare `repair_evidence_obligations`, and `open-packet` already delivers
authorized input materials. The role-visible path is still too easy to
misread because the PM repair instruction shows a short `decision`/`reason`
example, the result skeleton is buried in the sealed packet body, and focused
tests still exercise the old short positive shape.

This change stabilizes the current-contract repair submission path without
lowering standards or adding compatibility surfaces.

## What Changes

- Surface the packet's authoritative submission checklist and
  `minimal_valid_shape` through `open-packet` as role-facing guidance.
- Rewrite PM repair packet instructions so the example comes from the current
  packet skeleton instead of a fixed `decision`/`reason` short form.
- Move PM repair pre-submit requirements to prominent role/card guidance,
  especially the rule that `repair_evidence_obligations` requires one
  `repair_obligation_disposition` row per obligation id.
- Update focused high-standard repair tests so positive PM repair paths submit
  the current complete shape, while reason-only PM repair remains a negative
  case.
- Keep secondary matrices and FlowGuard model checks as proof tools, not new
  FlowPilot runtime protocol fields.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `blocker-repair-policy`: PM repair packets must expose and use the current
  packet's authoritative submission skeleton when repair obligations exist.
- `packet-open-authority-exits`: successful `open-packet` must present the
  role-visible submission checklist alongside sealed packet and authorized
  input materials.
- `role-output-transaction-boundaries`: role submissions must treat the
  runtime-provided packet skeleton as the current mechanical checklist before
  `submit-result`.

## Impact

- Runtime PM repair packet body text and `open-packet` JSON output.
- Runtime role handoff text.
- FlowPilot PM role and PM repair phase prompt cards.
- Focused high-standard control-flow tests and related model-test alignment
  evidence.
- Local install sync and install audit after prompt/runtime changes.
