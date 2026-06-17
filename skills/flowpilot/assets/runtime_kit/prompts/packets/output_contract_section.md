
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
- Treat only `output_contract`, `current_handoff_contract.required_report_contract`,
  and `submission_checklist` as mechanical field authority. Packet body
  explanation text can describe the work, but it does not create hidden
  required fields or alternate field names.
- If `output_contract.allowed_value_options` or
  `current_handoff_contract.required_report_contract.allowed_value_options`
  names a field, that field is a finite menu. Choose exactly one listed value
  for that field. Do not invent synonyms, prose variants, extra enum values, or
  blank placeholders.
- If `output_contract.field_type_requirements`,
  `current_handoff_contract.required_report_contract.field_type_requirements`,
  or `submission_checklist.field_type_requirements` names a field, use that
  exact JSON type and literal value family. A field that requires boolean
  `true` must be the literal value `true`, not an object or explanation text.
- When `flowpilot_new.py open-packet` returns `submission_checklist.result_skeleton` or the packet body includes `minimal_valid_shape`, use it as the current mechanical example before `submit-result`.
- When the contract requires `pm_visible_summary`, write a non-empty short summary list yourself; runtime relays it to PM and does not synthesize it.
- When the packet includes `authorized_result_reads`, use every required result body delivered by `flowpilot_new.py open-packet`; summaries are navigation aids, not substitutes for delivered bodies, and one delivered body is not a substitute for another.
- Include every required field even when the value is `[]`, `false`, or `null`.
- If the work cannot satisfy the contract, return a blocked or needs-PM result body that still includes every required field and a `Contract Self-Check` section.
- You may add a short `controller_aside` only to the runtime progress/status or returned envelope. It is Controller-only process/status metadata, not formal work content, evidence, findings, recommendations, decisions, approvals, or a Router event source.

${required_sections_block}${required_envelope_block}${required_values_block}${allowed_decisions_block}${segment_values_block}${body_template_block}Before returning, write a `Contract Self-Check` section in the sealed result, report, or decision body. If any required field, evidence item, or section is missing, return `blocked` or `needs_pm` instead of a pass.
