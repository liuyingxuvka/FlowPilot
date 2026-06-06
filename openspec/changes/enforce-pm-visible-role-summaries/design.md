## Design

### Two Complementary Channels

FlowPilot uses two complementary handoff channels:

- `pm_visible_summary`: short role-authored text for PM to locate what happened
  quickly.
- `authorized_result_reads`: runtime-authorized sealed body access for formal
  judgement.

The summary never replaces the authorized body read. A PM packet may contain
both. PM uses the summary to know where to look, then opens the required body
when the packet grants and requires that read.

### Role-Authored Summary Field

Formal non-PM role results must include:

```json
"pm_visible_summary": [
  "One short PM-readable statement of what this role found, fixed, or still requires."
]
```

The field is deliberately small and role-authored. Runtime may validate that it
exists and relay the exact strings with source metadata. Runtime must not
generate a replacement summary from sealed packet or result bodies.

This applies to worker, FlowGuard operator, and Reviewer result packets. PM
repair decisions and PM disposition packets keep their existing decision/reason
contracts, because those are already PM-authored decision records.

### PM Context Propagation

PM packets receive a `recent_role_report_summary` array built from accepted or
semantically blocking current-run role results. Each entry includes only source
metadata plus the role-authored summary:

```json
{
  "role": "reviewer",
  "packet_id": "packet-0004",
  "result_id": "result-0004",
  "packet_kind": "review",
  "summary": [
    "Reviewer found stale path data/product/projectradar_lifecycle.json and requires data/product/projectradar_project_lifecycle.json."
  ],
  "summary_is_navigation_only": true,
  "formal_judgement_requires_authorized_body_read": true
}
```

This preserves the sealed-body boundary. PM sees the role's public navigation
summary, not the sealed body content. When the PM packet also carries
`authorized_result_reads`, PM must open those bodies before submitting any
decision that requires them.

### Authorized Result Reads

Packets may include an `authorized_result_reads` array. Each row grants the
current packet recipient access to one existing result/report body:

```json
{
  "result_id": "result-0181",
  "source_packet_id": "packet-0177",
  "source_role": "reviewer",
  "purpose": "reviewer_block_report_for_pm_repair",
  "required_before_submit": true,
  "allowed_roles": ["pm"]
}
```

Runtime fills mechanical metadata such as body hash from the source result.
Runtime must not copy the sealed body, summarize it, or make the PM decision
from it. The recipient role opens the body through the runtime command and uses
it inside its own role boundary.

### Missing Summary Handling

After ordinary mechanical checks pass and before any semantic outcome is
accepted, runtime validates the required summary. If the field is missing,
empty, or not a list of non-empty strings, runtime marks the result as a current
contract failure and reissues the same current packet family. That keeps the
repair small and avoids creating a separate summary workflow or ledger.

### Concrete Repair Guidance

When a blocking role result provides `blocking_findings` entries with
`required_repair`, runtime records those strings as PM-facing repair guidance.
The PM repair-decision packet uses this concrete guidance before generic
generic text such as "reviewer reported block".

This is narrow structured extraction. It accepts current result fields; it does
not parse arbitrary prose or infer repairs from sealed body text.

### Non-Goals

- Do not let summaries satisfy required body-read receipts.
- Do not let Controller read sealed bodies.
- Do not add runtime prose summarization.
- Do not collapse the user's desired fresh repair node policy.
