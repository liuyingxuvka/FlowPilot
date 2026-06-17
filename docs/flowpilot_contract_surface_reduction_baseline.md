# FlowPilot Contract Surface Reduction Baseline

## Purpose

This document is the human-readable baseline for the
`reduce-flowpilot-contract-surface` change. It records why FlowPilot is being
contracted back to one clear current protocol, and how the historical successful
route is used without restoring old field bloat or fallback surfaces.

The active `harden-flowpilot-stage-evidence-matrix` change remains related
evidence for stage-matrix hardening. This baseline does not replace that change;
it explains the higher-level contraction rule used by
`reduce-flowpilot-contract-surface`.

## Process Baseline

The historical WorldGuard run `run-20260613-140526` is process evidence, not a
field contract. Its useful lesson is that FlowPilot can move smoothly when each
role has one job and one handoff path:

1. PM writes the current packet for the current stage.
2. Runtime checks only mechanical validity, current ids, field shape, and
   fixed blocker routing.
3. FlowGuard models process, state, evidence freshness, and repair risk inside
   the assigned work order.
4. Reviewer checks current-stage quality and evidence, then blocks only with a
   blocker class allowed for that subject.
5. PM absorbs FlowGuard/Reviewer findings and chooses the next structured
   repair or continuation decision.

The later first-packet failure is regression evidence. Its useful lesson is
that terminal, worker, or model-detail obligations must not leak into early
preplanning packets. A first package can define requirements and acceptance
items without final replay, worker output, or target-product proof.

## Field Baseline

The historical run does not freeze the old field set. Fields must be judged by
the current lifecycle:

- keep: the field is necessary for exactly one current packet family;
- move: the field is valid, but belongs to one later packet family;
- delete: the field is not part of the current contract and must be rejected
  instead of translated.

This keeps the route strict without making early packets carry future evidence.
Strictness belongs at the correct stage; it is not a global requirement pasted
onto every packet.

## Role Boundary Baseline

Runtime owns mechanical validity:

- packet/result/current-run ids;
- schema and required fields;
- fixed blocker enum membership;
- fixed blocker handling route;
- rejection of old aliases, wrappers, missing-field defaults, fallback parsing,
  and historical-result promotion.

FlowGuard owns model/process review:

- process and state risks;
- evidence freshness;
- model/test gaps;
- repair return paths;
- current evidence file details.

Reviewer owns human-quality review:

- whether the current artifact satisfies the current-stage contract;
- whether evidence is credible;
- whether contradictions or hard quality failures remain;
- whether a current-stage blocker is needed.

PM owns semantic route decisions:

- absorbing FlowGuard and Reviewer reports;
- choosing the finite repair branch from a PM repair-decision packet;
- deciding whether to repair current scope, repair parent scope, redesign the
  route, stop for the user, or waive with authority.

Blockers do not preselect PM's repair branch. A blocker selects the handling
route. For PM-owned substantive blockers, that handling route is the current
PM repair-decision packet.

## Repair Baseline

Every blocker class must have one declared handling route and one repair packet
contract. A repeated repair must carry prior repair materials forward so the
next role can see what was tried and why it did not close.

Two repair-loop limits must stay separate:

- ordinary same-lineage repair loops use the five-attempt break-glass threshold;
- terminal supplemental repair contracts use the separate three-round hard cap.

A fourth terminal supplemental round is not a fallback path. PM must choose a
legal terminal disposition, stop for the user, or route a new PM decision from
the current blocker context.

## Current Evidence Baseline

Current evidence must come from the current packet/run surface. Historical
artifacts may explain why a rule exists, but they do not prove current
completion. Target projects must rely on the installed FlowPilot runtime,
run-local evidence, and installed self-check receipts; they must not require
the FlowPilot development repository's simulation scripts.

## Maintenance Rule

Future repairs should first ask:

1. Is this a real current-runtime blocker, or a stale prompt/model/test
   mismatch?
2. Which role owns the check: Runtime, FlowGuard, Reviewer, or PM?
3. Which packet family owns the field at this lifecycle stage?
4. Is the old surface deleted, moved, or explicitly kept?
5. Does a negative test prove unsupported aliases and fallback paths stay
   rejected?

If the answer is unclear, reduce the repair plan before adding fields, packets,
roles, or compatibility paths.
