## 1. Scope And Preflight

- [x] 1.1 Run predictive KB preflight, FlowGuard package/version audit, project audit, and existing-model orientation.
- [x] 1.2 Read project handoff, preflight findings, topology, and relevant existing OpenSpec specs.
- [x] 1.3 Identify peer-agent changes and avoid reverting the PM repair submission change.

## 2. Current Packet Checklist

- [x] 2.1 Extend `open-packet` `submission_checklist` to consume `current_handoff_contract.required_report_contract`.
- [x] 2.2 Include branch-valid shapes, child fields, explicit/non-empty arrays, forbidden fields, downstream consumer, material manifest, and required result-read obligations.
- [x] 2.3 Update handoff guidance to name the checklist as the role's pre-submit mechanical shape.

## 3. Role-Facing Prompt And Payload Surfaces

- [x] 3.1 Replace stale role-card command examples with current `open-packet`, `submit-result`, and `progress` commands.
- [x] 3.2 Replace generated role-facing old command text in payload/protocol/wait contract sources.
- [x] 3.3 Extend prompt coverage to scan current generated role-facing Python sources.

## 4. Field Lifecycle Alias Rejection

- [x] 4.1 Reject PM package disposition and formal gate payloads that provide only `reason` instead of `decision_reason`.
- [x] 4.2 Reject material-sufficiency payloads that provide only `checked_by_role` or `runtime_open_receipts` aliases.
- [x] 4.3 Reject PM request payloads that provide only `mode`, `from_role`, `recipient_role`, or `kind` aliases.
- [x] 4.4 Reject research packet specs that provide only `recipient_role` instead of `to_role`.

## 5. Test And Model Alignment

- [x] 5.1 Add focused unit tests for complete checklist projection from the handoff contract.
- [x] 5.2 Add focused negative tests for removed alias/fallback fields.
- [x] 5.3 Update FlowGuard field-contract and prompt-coverage model checks for the new obligations.
- [x] 5.4 Add the research packet `recipient_role` alias miss to FieldLifecycleMesh, ContractExhaustionMesh, and Cartesian bridge coverage.

## 6. Validation, Install, And Sync

- [x] 6.1 Run focused unit tests and FlowGuard checks for prompt, packet, field, and alignment surfaces.
- [x] 6.2 Run or start background parent regressions using the repository background log contract and inspect completion artifacts before claiming results.
- [x] 6.3 Rebuild and check project topology after model/test/prompt changes.
- [x] 6.4 Sync repository-owned FlowPilot install artifacts to the local installed skill and run install audits.
- [x] 6.5 Update FlowGuard adoption logs with commands, evidence, scoped gaps, and peer-write caveats.

## 7. Closure

- [x] 7.1 Run OpenSpec validation for this change.
- [x] 7.2 Inspect final git diff without reverting unrelated peer-agent work.
- [x] 7.3 Record predictive KB postflight observation if this work exposes a reusable route gap.
