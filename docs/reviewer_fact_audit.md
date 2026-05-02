# Reviewer Fact Audit

Date: 2026-05-02

## Scope

This audit checks whether FlowPilot reviewer gates require direct factual
review or can be satisfied by reading worker/PM summaries.

## Findings

1. Startup activation previously depended on a separate runtime startup check.
   That path is removed. Startup now has only a human-like reviewer factual
   report and a PM-owned startup opening decision. The reviewer must check real
   state/frontier/route, crew, role memory, automation records, Windows
   scheduled task evidence, watchdog evidence, global supervisor evidence,
   background-agent user decision versus actual subagent state, live subagent
   count plus current-task freshness or explicit single-agent fallback
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

## New Baseline

Reviewer decisions that cite only worker or PM summaries are invalid. Worker
reports can point to evidence, but reviewer-owned gates must name the direct
facts checked for the gate.

## Follow-Up Watch Points

- Future reviewer templates should include a `worker_report_only: false` or
  equivalent field when the gate can otherwise be confused with a summary
  review.
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
