## Why

Recent live FlowPilot work showed two small process frictions: PM node
acceptance plans can stay too abstract about the current executable check
surface, and Controller status messages do not reliably carry the runtime-owned
expanded-node fraction when a user-facing status update is already happening.
Both issues are already covered by existing route, review, and status surfaces,
so the repair should strengthen those surfaces instead of adding fields or a
new workflow.

## What Changes

- Strengthen PM node acceptance guidance so a worker-ready node plan must
  explain the current files/artifacts, checker or validation surface, status
  vocabulary, and expected failure shape when those details are relevant.
- Make unclear current check surfaces feed the existing node-boundary decision:
  PM should consider whether the apparent leaf is too broad or under-split and,
  when needed, use the existing `redesign_route` path with a replacement
  parent/module and ordered child nodes.
- Strengthen Reviewer node-plan review guidance to block abstract plans that
  leave check surfaces, status vocabulary, failure shapes, node boundaries, or
  worker outcome definition for Worker invention.
- Make Controller prompt guidance say that when a user-facing status update is
  already appropriate, any available runtime-owned `progress_fraction.display`
  should normally be included; node-fraction changes may receive a short status
  line, but internal patrol, receipt, ACK, and ledger noise remains quiet.
- Keep the repair current-contract and minimal: no new schema fields, no
  compatibility path, no fallback, no README/document-specific rule, and no
  child-skill edits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `formal-gate-review-standards`: PM node acceptance planning and Reviewer
  node-plan review must make the current executable check surface concrete
  before worker dispatch.
- `controller-user-status`: Controller status guidance must reuse the existing
  runtime-owned expanded-node fraction more consistently during legitimate
  user-facing status updates.
- `flowpilot-prompt-boundary-policy`: Prompt/card guidance must keep this
  repair inside existing prompt boundaries without adding schema fields,
  fallback surfaces, or artifact-specific special cases.

## Impact

- Affected prompt cards: PM node acceptance plan, Reviewer node acceptance plan
  review, Controller core, Controller resume reentry, Controller action-ledger
  table prompt, and the FlowPilot launcher guidance.
- Affected tests/models: prompt/card instruction coverage, focused planning
  quality coverage, focused controller patrol/status coverage, and existing
  producer-before-consumer checks to confirm this change does not create a
  README-specific ordering rule.
- Affected validation: OpenSpec validation, targeted FlowGuard/model checks,
  focused unit tests, topology rebuild/check when prompt/test/model surfaces
  change, and local installed-skill sync/audit.
