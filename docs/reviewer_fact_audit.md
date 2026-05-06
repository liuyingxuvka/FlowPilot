# Reviewer Fact Audit

Date: 2026-05-02

Updated: 2026-05-06

## Scope

This audit checks whether FlowPilot reviewer gates require direct factual
review or can be satisfied by reading worker/PM summaries.

## Findings

1. Startup activation previously depended on a separate runtime startup check.
   That path is removed. Startup now has only a human-like reviewer factual
   report and a PM-owned startup opening decision. The reviewer must check real
   state/frontier/route, crew, role memory, heartbeat or manual-resume
   evidence, background-agent user decision versus actual subagent state, live
   subagent count plus current-task freshness or explicit single-agent fallback
   authorization, and cleanup boundary. PM may open only from a clean factual
   report.
2. Live-subagent review is not a count-only check. For every new formal
   FlowPilot task where the user authorizes background agents, the reviewer
   must verify that all six role-bearing subagents were freshly spawned after
   the current startup answers and current route allocation. Historical
   `agent_id` values from prior crew ledgers or older role-memory packets are
   audit history only and must be listed as reused-ID blockers if they appear
   in current live-agent evidence.
3. Human-like implementation inspection already requires context loading,
   neutral observation, real product/output inspection, and same-inspector
   recheck after repair. This is factual review, not report-only review.
4. Composite and final backward reviews already require reloading child
   evidence, route/frontier/ledger state, and delivered product evidence before
   closure. This is factual replay, not report-only review.
5. Child-skill gates already require source skill loading, mapped gates,
   evidence audit, output/evidence match, domain-quality review, loop closure,
   and assigned-role approval. This is factual review when the evidence audit
   and output match records are complete.
6. Material sufficiency wording was too easy to read as packet-only review.
   It now requires the reviewer to open or sample actual materials and record
   direct source checks.
7. Product-function architecture usefulness challenge wording was too easy to
   read as PM-package-only review. It now requires comparison against the user
   request, inspected materials, and expected workflow reality.
8. UI screenshot, browser, desktop, interaction, and aesthetic gates had a
   weaker path: automated screenshot QA or worker interaction logs could be
   treated as enough evidence if the reviewer wrote only an aesthetic or
   pass/fail summary. These gates now require reviewer-owned personal
   walkthrough evidence, reachability checks, overlap/clipping checks,
   whitespace/density/crowding review, and concrete design recommendations.
9. The same weakness existed outside UI: some PM, reviewer, and FlowGuard
   officer approvals could still read as "approve after reviewing the evidence
   packet." All role approvals now require independent adversarial validation:
   direct source/state probes, concrete evidence references, failure
   hypotheses tested, and residual blindspots. Startup PM opening, material
   sufficiency, product architecture, child-skill manifests, FlowGuard model
   approvals, node/composite/final human review, final product replay, and
   final ledger approval are all covered.

## New Baseline

Router-owned checks may replace reviewer effort only when the router writes a
proof-carrying audit from evidence it can recompute or bind to the current run:
router-computed state, packet-runtime body/envelope hashes, or explicit host
receipts. Payload booleans, AI statements, default-option claims, Controller
summaries, and role reports are not proof. Router proofs replace only
mechanical checks; live facts, user-intent authenticity without a host receipt,
source quality, product/visual judgement, and backward replay remain reviewer
owned.

Reviewer, PM, and FlowGuard officer decisions that cite only worker, PM, or
other-role summaries are invalid. Reports can point to evidence, but
role-owned gates must name the direct facts checked, adversarial hypotheses
tested, and concrete evidence references used for the decision.

Every packet review also requires an explicit envelope-aware role-origin audit.
The router/packet runtime now persists the mechanical packet audit and a
`flowpilot.router_owned_check_proof.v1` sidecar for hash-backed envelope/body
checks. The reviewer must still inspect the actual result quality, acceptance
slice fit, freshness, role origin, and contamination risk before any pass.
Controller, unknown-origin, wrong-role, cosigned/relabelled wrong-role results,
body-hash mismatches, stale body reuse, or controller body access are blocking
findings. Role-origin mismatches are `block_invalid_role_origin`, require a
controller-boundary warning, and must be returned to PM for reissue or repair by
the assigned role.

## Follow-Up Watch Points

- Future reviewer templates should include a `worker_report_only: false` or
  equivalent field when the gate can otherwise be confused with a summary
  review.
- UI and visual reviewer templates should include
  `reviewer_personal_walkthrough_done`, direct screenshot/surface paths,
  interaction paths exercised, unreachable controls, text overlap/clipping,
  whitespace/density/crowding findings, aesthetic verdict, and design
  recommendations. A human-review gate should block or request more evidence
  when the reviewer cannot personally operate the surface.
- Startup reviewer reports should include `current_task_fresh_agents: true`,
  `reused_historical_agent_ids: []`, and direct evidence paths for current
  agent birth or spawn time when live background agents are authorized.
- Startup reviewer reports must also include current-run isolation evidence:
  `.flowpilot/current.json`, `.flowpilot/index.json`, current run manifest,
  current-run state/frontier/route paths, top-level legacy control-state
  quarantine status, and a prior-work import packet when the run continues old
  work.
- FlowGuard model labels should prefer `fact_report`, `neutral_observation`,
  `evidence_audited`, `evidence_matches_outputs`, or `backward_checked` over
  generic `reviewed` when direct factual review is required.
