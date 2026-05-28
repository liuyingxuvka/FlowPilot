## Context

FlowPilot currently has strong runtime authority boundaries: Controller relays,
PM decides, Officers model, Reviewers inspect, and Workers execute bounded
packets. It also already references FlowGuard in startup capability snapshots,
product/process modeling plans, officer reports, test obligation matrices, and
final ledgers.

The remaining problem is duplication. Many cards still encode fixed
FlowPilot-local planning, routing, repair, evidence, and completion rules as
prompt checklists. That keeps FlowGuard present but not consistently used as
the default method for non-trivial role judgement.

This design introduces a narrow protocol layer:

- `FlowGuard Work Order`: a run-scoped request for a specific FlowGuard
  modeling, validation, freshness, repair, mesh, or alignment question.
- `FlowGuard Report`: a run-scoped answer produced by a formal role, usually a
  FlowGuard Officer, citing the FlowGuard route used, evidence, skipped checks,
  confidence boundary, and PM decision impact.
- `FlowGuard Status Reference`: compact ids/paths/hashes/freshness fields that
  can be carried in PM decisions, packets, reviewer packages, events, resume
  records, and final ledgers without exposing sealed bodies in chat.

FlowPilot remains the authority and delivery system. FlowGuard becomes the
common analysis method.

## Goals / Non-Goals

**Goals:**

- Make FlowGuard the default path for non-trivial product, process, skill,
  acceptance, validation, repair, evidence, resume, and closure judgement.
- Keep PM as the decision owner. FlowGuard reports support PM decisions; they
  do not mutate routes or approve completion by themselves.
- Keep Reviewer as the human-like independent gate. Reviewer checks both the
  reviewed artifact and the FlowGuard evidence that artifact depends on.
- Keep Worker authority packet-scoped. Workers satisfy assigned FlowGuard
  obligations inside their packet or report a bounded gap.
- Keep Controller relay-only. Controller may show FlowGuard status but cannot
  interpret reports or approve gates.
- Prefer updating existing cards and validation over broad runtime rewrites.

**Non-Goals:**

- Do not replace FlowPilot's Router, packets, role identities, ledgers,
  runtime return paths, or sealed-body boundaries.
- Do not turn FlowGuard into an optional ordinary child skill.
- Do not give Officers, Reviewers, Workers, or Controller PM authority.
- Do not require FlowGuard ceremony for trivial copy, formatting, or mechanical
  work with no product/process/evidence risk.
- Do not archive or modify unrelated active OpenSpec changes.

## Decisions

### Decision: Use a shared work-order/report vocabulary instead of duplicating card checklists

The new protocol will add the terms `FlowGuard Work Order`,
`FlowGuard Report`, `flowguard_work_order_id`, `flowguard_report_id`,
`flowguard_report_freshness`, `flowguard_route_used`, and
`flowguard_pm_acceptance` to the core cards and validation checks.

Rationale: Cards can stay role-specific while pointing to the same artifact
contract. This reduces prompt drift and prevents separate PM, Officer,
Reviewer, and Worker versions of the same FlowGuard rule.

Alternative considered: Rewrite every phase card with bespoke FlowGuard
instructions. Rejected because it increases duplicated text and makes future
FlowGuard route changes harder to propagate.

### Decision: Prompt-first implementation with focused validation, then runtime enforcement

This change first hardens the prompt contract and tests that the core runtime
cards carry the new obligations. Router-level schema enforcement can be added
incrementally after the prompt vocabulary is stable.

Rationale: The current request targets system cards and workflow prompts.
Prompt and test updates are lower risk under parallel agent work than broad
runtime schema changes.

Alternative considered: Add full Router artifact validators immediately.
Deferred because several peers are editing router and simulation files now,
and the same behavioral contract can be introduced safely through cards,
OpenSpec, focused tests, and FlowGuard modeling first.

### Decision: Existing FlowGuard model boundaries are extended by a focused child model

The broad `meta_model.py` and `capability_model.py` already cover the formal
FlowPilot route, FlowGuard modeling coverage, test obligations, child-skill
selection, and closure gates. This change will add a focused model/check for
role FlowGuard work-order integration rather than first editing oversized
parent models.

Rationale: A focused child model can prove the new obligation chain without
destabilizing large parent-model proofs. Parent model updates can follow once
the child evidence is current.

Alternative considered: Edit the parent meta and capability models first.
Rejected because the parent models are large and already have active generated
result files in the dirty worktree.

### Decision: Reviewer validates FlowGuard evidence freshness, not report contents by chat

Reviewer cards will require direct review of referenced artifacts and status
fields. Reviewer blocks missing, stale, progress-only, wrongly scoped, or
unaccepted reports. Reviewer does not paste or discuss sealed report bodies in
Controller chat.

Rationale: This preserves sealed-body boundaries while making FlowGuard
evidence reviewable.

### Decision: Workers receive obligations, not route authority

Worker packets may include FlowGuard-derived obligations and test rows.
Workers return `FlowGuard Obligation Coverage` or existing
`Test Obligation Coverage` rows for assigned obligations. If the obligation
requires broader FlowGuard work, the worker returns `needs_pm`, `blocked`, or
a PM Suggestion Item.

Rationale: This lets every worker use FlowGuard-shaped evidence without making
workers mini-PMs.

## Risks / Trade-offs

- [Risk] Prompt text grows and becomes harder to maintain. → Mitigation:
  centralize common language around work-order/report vocabulary and use
  focused tests that look for required markers only on core cards.
- [Risk] FlowGuard becomes ceremony for trivial work. → Mitigation: cards
  require FlowGuard for non-trivial decisions and allow scoped waiver/reason
  for trivial or already mechanically covered work.
- [Risk] Officers appear to approve gates. → Mitigation: officer cards keep
  "report supports PM decisions, cannot approve gates or mutate routes"
  wording and validation checks preserve authority boundaries.
- [Risk] Reviewer duplicates Officer modeling. → Mitigation: reviewer checks
  report existence, freshness, scope, skipped checks, and acceptance; deeper
  reruns require PM routing.
- [Risk] Parallel agent edits stale validation evidence. → Mitigation: avoid
  rewriting unrelated dirty files, run targeted tests after edits, and run
  heavy regression through background artifacts before claiming completion.
