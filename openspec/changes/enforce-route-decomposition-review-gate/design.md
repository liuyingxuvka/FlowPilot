## Context

FlowPilot already has a current-contract planning packet, strict route-plan
JSON, post-result FlowGuard checks, Reviewer checks, semantic blockers, PM
repair decisions, and route materialization only after the planning result
passes review. A previous change also added mechanical refusal for parent/module
or child-bearing nodes that reach Worker dispatch.

The remaining gap is route quality before materialization. A broad leaf can
pass mechanically because the schema only knows it has an id and title. That is
intentional: "is this leaf small enough?" is not a pure shape question. The
right owner is Reviewer, supported by FlowGuard Operator process evidence and
PM replan authority.

## Goals

- Preserve one canonical executable route and existing current-contract repair
  loops.
- Make PM plan small worker-ready leaves at first planning time, not after a
  Worker starts.
- Let FlowGuard Operator detect routes that leak planning decisions into Worker
  execution.
- Let Reviewer block under-decomposed, overlapping, or worker-replanning
  leaves and request PM route deepening before materialization.
- Keep the field surface small.

## Non-Goals

- Do not add a second PM-authored display plan.
- Do not require many new route-node explanation fields.
- Do not make every simple task artificially nested.
- Do not let Reviewer become the route author; Reviewer can propose a split,
  but PM must submit the repaired route.

## Design

1. **PM planning packet carries the gate.**

   The planning packet acceptance criteria and body should tell PM that the
   route will not materialize unless Reviewer can see worker-ready leaves. This
   is prompt guidance, not persistent node schema.

2. **FlowGuard Operator checks process viability.**

   Operator should report whether the route can be traversed from planning to
   closure without letting Workers invent missing child routes. This supports
   Reviewer but does not replace Reviewer.

3. **Reviewer owns the semantic decomposition decision.**

   Reviewer blocks if a leaf has multiple deliverables, several ordered work
   phases, hidden child decisions, overlapping scope with siblings, or cannot be
   completed by one bounded Worker packet. Reviewer should return a concrete
   split recommendation in the existing `recommended_resolution` path.

4. **PM repair loop reuses existing blocker flow.**

   A Reviewer block on planning leaves the planning result unmaterialized,
   opens a PM repair decision, then issues a fresh planning packet after PM
   chooses current-scope repair. No special new repair family is needed.

5. **Node-entry splitting is fallback, not primary.**

   If a leaf still proves too broad at node acceptance planning, Reviewer should
   block that node plan and request route mutation/deepening before any Worker
   packet. This is a safety net for missed planning, not the default workflow.

## Validation

- OpenSpec strict validation for this change.
- Unit tests for planning packet route-quality criteria.
- Unit tests for Reviewer-blocked planning not materializing route nodes and
  routing back to PM repair.
- Card coverage tests for PM, FlowGuard Operator, Reviewer, and node-entry
  fallback language.
- Targeted FlowPilot tests plus FlowGuard model/test-alignment checks.
- Installed local FlowPilot sync and installed skill audit after source checks.
