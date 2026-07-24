
## Output Contract

This packet uses the system-selected FlowPilot output contract below. The recipient must satisfy it before returning an envelope.

```json
$json_contract
```

## Report Contract For This Task

This task packet is the source of truth for the result, report, or decision body. Do not rely on role-startup memory, chat history, or field-name guesses.

- Write the full body only to the sealed run-scoped body path requested by the packet.
- Return in chat only the controller-visible envelope. Do not include body content, findings, blockers, or evidence details in chat.
- Use the exact field names and exact required values from this contract. Do not rename fields with synonyms.
- Use only the current `path`/`hash` field names projected by this contract. Do
  not use or invent legacy `*_sha256` hash aliases; the current runtime does
  not accept them.
- Treat only the `submission_checklist.v2` returned by the current
  `flowpilot_new.py open-packet` call as role-facing mechanical field
  authority. `output_contract` and `current_handoff_contract.v2` are
  runtime-owned sources projected into that checklist; packet-body mirrors are
  not an alternate role-facing contract.
- If `submission_checklist.allowed_value_options` names a field, that field is
  a finite menu. Choose exactly one listed value
  for that field. Do not invent synonyms, prose variants, extra enum values, or
  blank placeholders.
- If `submission_checklist.field_type_requirements` names a field, use that
  exact JSON type and literal value family. A field that requires boolean
  `true` must be the literal value `true`, not an object or explanation text.
- Use `submission_checklist.result_skeleton` and the selected
  `submission_checklist.branch_valid_shapes` row as the current mechanical
  example before `submit-result`. Never generate a positive result from a
  packet-body `minimal_valid_shape`, required-field list, conditional-field
  map, or old checklist.
- When the contract requires `pm_visible_summary`, write a non-empty short summary list yourself; runtime relays it to PM and does not synthesize it.
- When the packet includes `authorized_result_reads`, use every required result body delivered by `flowpilot_new.py open-packet`; summaries are navigation aids, not substitutes for delivered bodies, and one delivered body is not a substitute for another.
- Include every required field even when the value is `[]`, `false`, or `null`.
- If the work cannot satisfy the contract, return a blocked or needs-PM result body that still includes every required field and a `Contract Self-Check` section.
- You may add a short `controller_aside` only to the runtime progress/status or returned envelope. It is Controller-only process/status metadata, not formal work content, evidence, findings, recommendations, decisions, approvals, or a Router event source.

Every substantive role must also complete the semantic
`contract_self_check.workstream_plan_and_completion` section projected in the
current skeleton. It is the sole role plan: write it before execution, use one
row per acceptance obligation or meaningful phase, and update those same rows
through submission with completion status, evidence refs, deviations and unresolved
work, plus delegation/integration, verification and repair. Do not create rows
for commands, file reads, polls, or other microsteps, and do not copy a second
final plan. Reviewer cites this table and reports differences, gaps, and
judgment rather than reproducing the complete table. Runtime does not
mechanically score the quality of this section; Reviewer compares it with the
actual current artifact and evidence through the existing review/repair path.
Controller is excluded because its Runtime-derived foreground action ledger is
its only plan.

Before writing that plan, reconstruct the role-scoped global target from the
current packet, node context, and current authoritative references. List all
packet-owned hard obligations and unresolved evidence before optional
improvements, then order the work by dependency and risk rather than by what is
easiest to mark complete. A mandatory reference that is missing, generic,
stale, cross-run, or inaccessible requires the blocker or PM-routing outcome
allowed by the current contract instead of a guessed standard. In the existing result fields and
numbered plan, every completion claim must preserve the closure triangle:
accepted goal or current obligation -> actual artifact or observable state ->
current direct evidence. If any side is absent, report the obligation as
unresolved or blocked. Do not add a result field for this semantic check.

${required_sections_block}${required_envelope_block}${required_values_block}${allowed_decisions_block}${segment_values_block}${body_template_block}Before returning, write a `Contract Self-Check` section in the sealed result, report, or decision body. If any required field, evidence item, or section is missing, return `blocked` or `needs_pm` instead of a pass.
