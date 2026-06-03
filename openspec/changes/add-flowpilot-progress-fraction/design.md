## Context

FlowPilot's runtime already owns the structured view of current-run packets,
route nodes, result envelopes, and control-plane actions. The Controller is
intentionally restricted to public envelopes and runtime hints, so progress
reporting must come from the runtime rather than Controller-side inference.

This change adds one lightweight public signal: current expanded node progress
as `ended_nodes/expanded_nodes`.

## Goals / Non-Goals

**Goals:**

- Provide one runtime-owned progress fraction on public runtime outputs.
- Keep the fraction dynamic: it reflects the nodes currently expanded by the
  runtime, including repair nodes.
- Keep all counted work nodes equal weight.
- Let the Controller occasionally relay the fraction in user-facing status
  updates.
- Preserve sealed packet body boundaries and existing completion gates.

**Non-Goals:**

- No percent progress.
- No separate mainline/repair progress concepts.
- No UI work.
- No Controller-side counting, route parsing, or sealed-body inspection.
- No hard enforcement that every Controller message must include progress.

## Decisions

- **Runtime computes the fraction.** The runtime already owns current-run
  structured state and can expose an envelope-safe summary. Alternative:
  Controller calculation was rejected because it would duplicate runtime logic
  and risk sealed-body boundary drift.

- **Fraction is the public contract.** The public object includes
  `ended_nodes`, `expanded_nodes`, and `display` such as `2/3`. Alternative:
  percent output was rejected because dynamic expansion can make percentages
  misleading and sticky near high values.

- **Equal node weight.** Parent, child, and repair work nodes all count as one.
  Alternative: weighted progress was rejected because it requires subjective
  task-size estimation and makes the feature harder to reason about.

- **Control-plane mechanics are excluded.** ACKs, leases, patrols, liveness
  checks, and role-assignment resolution are operational mechanics, not work
  nodes. They must not inflate the numerator or denominator.

- **Controller guidance is permissive.** The Controller is reminded to relay
  the fraction when useful, but absence of the field is not a blocker and the
  fraction does not change routing or closure authority.

## Risks / Trade-offs

- Dynamic expansion can make the denominator grow and the ratio move backward.
  Mitigation: expose the raw fraction rather than a percent.
- A runtime bug could count control-plane records as work nodes. Mitigation:
  add focused tests for excluded mechanical actions.
- Existing long-running checks may rewrite shared evidence artifacts while
  other agents are active. Mitigation: run focused checks first and send broad
  background-style outputs to isolated `tmp/` artifacts where supported.
