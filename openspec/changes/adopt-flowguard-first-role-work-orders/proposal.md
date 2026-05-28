## Why

FlowPilot already requires FlowGuard for product and process modeling, but many
role cards still embed fixed planning, routing, review, repair, and validation
rules directly in FlowPilot prompts. This makes FlowPilot duplicate FlowGuard
judgement instead of using FlowGuard as the default method for non-trivial
role work.

This change makes FlowGuard a first-class work-order/report mechanism used
across PM, Officer, Reviewer, Worker, Controller-resume, node, repair, and
closure flows while preserving FlowPilot as the authority, packet, ledger, and
role-boundary control plane.

## What Changes

- Introduce a run-scoped FlowGuard work-order/report contract for non-trivial
  product, process, capability, acceptance, validation, repair, resume, and
  closure decisions.
- Require PM to create or consume FlowGuard work orders before major route,
  product, child-skill, node-acceptance, repair, final-ledger, or closure
  decisions unless a scoped waiver explains why FlowGuard is not needed.
- Convert Product and Process FlowGuard Officer prompts from standalone
  checklist owners into FlowGuard work-order executors that choose the smallest
  applicable FlowGuard satellite route and return a uniform report.
- Extend Reviewer prompts so FlowGuard-backed gates check report existence,
  freshness, scope fit, skipped checks, progress-only evidence, and PM
  acceptance instead of accepting prose summaries.
- Extend Worker prompts so assigned packets carry local FlowGuard obligations
  and workers return packet-scoped obligation coverage without mutating routes.
- Extend Controller resume and break-glass prompts so Controller may surface
  FlowGuard work-order/report status but never interpret reports, approve
  gates, or replace PM/Reviewer/Officer authority.
- Add focused validation that the core runtime cards mention the FlowGuard
  work-order/report protocol and preserve role authority boundaries.
- Update local install synchronization and verification paths after source
  changes.

## Capabilities

### New Capabilities
- `flowguard-work-order-protocol`: Run-scoped FlowGuard work orders and reports
  used by FlowPilot roles as the common route for non-trivial modeling,
  validation, repair, evidence freshness, and completion-readiness questions.

### Modified Capabilities
- `flowguard-modeling-coverage`: Modeling coverage now flows through reusable
  FlowGuard work orders and reports instead of only PM modeling plans and
  officer-specific checklists.
- `role-child-skill-use`: Role-skill bindings now distinguish ordinary child
  skills from FlowGuard satellite routes and require evidence for FlowGuard
  work-order execution by each formal role.
- `flowpilot-prompt-boundary-policy`: Prompt boundary policy now requires
  FlowGuard work-order/report language where cards make non-trivial decisions,
  while preserving Router authority and sealed-body boundaries.
- `flowguard-test-obligation-ownership`: Test obligations now reference
  FlowGuard work-order/report ids as their source and treat stale, skipped, or
  progress-only reports as unresolved evidence.

## Impact

- Affected prompt cards under
  `skills/flowpilot/assets/runtime_kit/cards/`, especially PM phase cards,
  role core cards, Officer cards, Reviewer cards, and Controller system cards.
- Affected validation under `tests/test_flowpilot_card_instruction_coverage.py`
  and supporting prompt/card coverage checks.
- Affected documentation and adoption records under `docs/`.
- Local installed FlowPilot skill must be synchronized after source changes
  with the repository install/audit scripts.
