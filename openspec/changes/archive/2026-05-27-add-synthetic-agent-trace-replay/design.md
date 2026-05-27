## Context

FlowPilot coordinates AI roles through packet envelopes, sealed packet/result
bodies, router actions, role-output contracts, ledgers, route mutation records,
resume state, and final closure gates. Existing tests cover many individual
contracts, and FlowGuard models cover abstract process obligations, but a live
AI call is still too expensive and variable for routine regression testing.

The new test layer will replay deterministic fake role actions through the
real control-plane APIs. The fake data proves that FlowPilot handles realistic
role behavior, bad role behavior, and stale evidence without making live AI
calls or allowing fixture evidence to close live project gates.

## Goals / Non-Goals

**Goals:**

- Provide reusable synthetic trace packs for PM, Worker, Reviewer, and officer
  actions.
- Exercise real packet, result, hash, ledger, router, resume, and evidence
  classification paths.
- Pair positive traces with negative traces so every important control gate has
  a known bad input that fails at the expected point.
- Keep synthetic/fixture evidence visibly separate from live project evidence.
- Integrate the first trace packs into focused routine tests before expanding
  into broader router/integration tiers.

**Non-Goals:**

- Do not call live AI models from regression tests.
- Do not change the production role protocol unless a replay exposes a real
  product defect.
- Do not let synthetic evidence satisfy live completion, release, or final
  acceptance claims.
- Do not replace FlowGuard abstract models, model-test alignment, or long
  background regressions.

## Decisions

1. Use test-only trace helpers instead of production replay code.

   The first implementation should live under the test surface so it can reuse
   existing runtime APIs without adding new production state machinery. If the
   helper stabilizes, a later change can decide whether a production diagnostic
   command is worthwhile.

2. Represent traces as small named packages.

   Each trace package records role, starting setup, fake output, action steps,
   expected ledger fields, expected router state, expected blockers, and
   evidence kind. This makes coverage review possible without rereading every
   unittest body.

3. Drive real APIs, not raw state mutations.

   The helper must create packets through packet runtime functions, relay
   envelopes through controller/runtime functions, submit results through
   runtime functions, and inspect persisted artifacts afterward. Directly
   editing the final state is allowed only for test setup that existing tests
   already treat as controlled scaffolding.

4. Start with the first critical slice.

   The first slice covers packet happy path, ACK-only rejection, Controller
   sealed-body isolation, wrong role/agent/hash rejection, PM result
   disposition, raw-result rejection, stale-evidence protection, resume result
   handoff, fixture-evidence boundary, and progress-only background rejection.

5. Keep long regressions in background artifacts.

   Long model regressions should use the repository's existing background log
   contract. Progress output is liveness only. Completion requires exit
   artifact, final status, and inspected evidence.

## Risks / Trade-offs

- Synthetic traces could become unrealistic -> require trace packages to use
  real packet/runtime/router APIs and keep a final small end-to-end toy flow.
- Fixture evidence could be mistaken for live proof -> record evidence kind and
  assert fixture/synthetic evidence cannot close live completion gates.
- The helper could duplicate existing test scaffolding -> build on existing
  router runtime test base patterns where possible and keep the helper narrow.
- Background regressions can race install sync -> run install sync and install
  audit/check serially after owned source validation, not in parallel.
- Peer agents may touch nearby code -> keep write scope isolated and recheck
  git status before each validation/sync claim.
