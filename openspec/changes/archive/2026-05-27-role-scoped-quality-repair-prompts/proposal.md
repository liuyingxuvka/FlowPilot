## Why

FlowPilot work packets already require evidence and low-quality-success checks,
but they do not state the self-repair obligation in the packet body with enough
role-specific clarity. A blanket "fix bugs directly" instruction would improve
worker quality pressure but would also corrupt reviewer, officer, Controller,
and PM authority boundaries.

## What Changes

- Add role-scoped quality-repair wording for executable worker packets: workers
  must self-check, fix defects that are inside the packet's allowed scope and
  write authority, rerun required evidence, and only then return completion.
- Add authority-preserving variants for research/material-scan and officer
  report packets: roles must correct their own report/model/evidence defects,
  while target-product or route defects become blockers, findings, or PM
  suggestion items.
- Add explicit anti-repair guidance for reviewer-facing packages: reviewers
  must challenge, block, request repair, or recommend PM routing, but must not
  repair the reviewed artifact directly.
- Add planning/model/test coverage so future prompt edits keep the inclusion
  and exclusion boundaries together.

## Capabilities

### New Capabilities
- `role-scoped-quality-repair-prompts`: Role-specific prompt obligations for
  packet self-check, in-scope worker repair, report/model self-correction, and
  reviewer anti-repair boundaries.

### Modified Capabilities
- `executable-repair-transactions`: Clarify that repair packets must carry the
  same in-scope quality-repair obligation when the selected plan authorizes
  bounded execution.
- `packet-open-authority-exits`: Clarify that successful packet open authorizes
  only role- and packet-bounded work, not cross-role silent repair.

## Impact

- Affected prompt surfaces: packet body template, PM packet-authoring cards,
  worker role cards, research/material-scan cards, officer request/report cards,
  reviewer cards, and repair-packet guidance.
- Affected verification: card-instruction coverage tests, planning-quality
  model/checks, and focused prompt-boundary tests.
- No API, dependency, or release/publish behavior change.
