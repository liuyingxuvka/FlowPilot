
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
- When the contract requires `pm_visible_summary`, write a non-empty short summary list yourself; runtime relays it to PM and does not synthesize it.
- When the packet includes `authorized_result_reads`, use the required result bodies delivered by `flowpilot_new.py open-packet`; summaries are navigation aids, not substitutes for delivered bodies.
- Include every required field even when the value is `[]`, `false`, or `null`.
- If the work cannot satisfy the contract, return a blocked or needs-PM result body that still includes every required field and a `Contract Self-Check` section.
- You may add a short `controller_aside` only to the runtime progress/status or returned envelope. It is Controller-only process/status metadata, not formal work content, evidence, findings, recommendations, decisions, approvals, or a Router event source.

${required_sections_block}${required_envelope_block}${required_values_block}${allowed_decisions_block}${segment_values_block}${body_template_block}Before returning, write a `Contract Self-Check` section in the sealed result, report, or decision body. If any required field, evidence item, or section is missing, return `blocked` or `needs_pm` instead of a pass.
