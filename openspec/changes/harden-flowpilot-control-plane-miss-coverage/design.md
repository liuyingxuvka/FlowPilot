## Context

FlowPilot already has runtime packet/result contracts, formal review gates,
break-glass repair, route-display refresh, and fake-AI rehearsal models. Recent
live runs showed that those pieces were individually present but not closed as a
single model-tested control plane:

- the role-replacement resolver said a reviewer self-review was forbidden, but
  the committed replacement still reused the same agent;
- the review row recorded `self_review` blockers, but system validation still
  treated the subject result as passed;
- formal reviewer reports could pass with an empty `pm_suggestion_items` list;
- final-closure blocker combinations could reach controller break-glass before
  the normal PM/runtime repair route had a legal next action;
- the route progress display could replace earlier nodes instead of preserving
  cumulative work;
- fake-AI matrices covered selected examples but did not generate same-class
  Cartesian cells for empty owner sets, self-review identity, formal attachment
  absence, review suggestion absence, or final-closure blocker combinations.

The repository rule remains: keep one current structured path per behavior. Do
not add compatibility shims, prose fallbacks, legacy aliases, or parallel
authority records.

## Goals / Non-Goals

**Goals:**

- Backfeed the live model misses into explicit FlowGuard and fake-AI coverage
  matrices.
- Repair the smallest runtime/controller/prompt paths that allowed the misses.
- Make each same-class family testable through current packet/result/gate
  surfaces and focused runtime tests.
- Preserve break-glass as the fifth-repeat or no-legal-next-action fuse, not as
  the normal repair path.
- Keep reviewer recommendations high-standard and PM-facing while hard blockers
  remain tied to minimum requirement failures, quantitative shortfalls, missing
  evidence, or protocol violations.

**Non-Goals:**

- No new reviewer-vs-PM arbitration loop.
- No new compatibility layer for older packet/result fields.
- No broad role taxonomy or per-agent timeout policy change in this change.
- No live-AI semantic evaluation claim from fake-AI tests.
- No change to frozen acceptance contracts in active user projects.

## Decisions

1. **Use current runtime gates as final authority for mechanical identity.**
   The role resolver may recommend `create_new_role`, but `lease_agent` is the
   last commit point. It must reject a replacement when the effective agent id
   still equals the forbidden prior agent id. This prevents controller or host
   payload mistakes from becoming accepted state.

2. **Treat review acceptance as part of system validation.**
   System validation must inspect the concrete review record, not only the
   existence of a review id. A review with `decision=block`, blockers, missing
   direct evidence, or non-independent producer/reviewer identity cannot satisfy
   validation even when the review body text says "pass".

3. **Make PM suggestions a review report contract, not a subject-quality
   blocker.** A formal reviewer pass must include nonempty
   `pm_suggestion_items`. Empty suggestions cause reissue of the review report
   contract. The reviewed work is blocked only when the reviewer identifies a
   minimum-standard failure, quantitative shortfall, missing evidence, or
   protocol violation.

4. **Represent progress as cumulative display state.** Route display remains a
   projection, not authority. The projection must preserve prior setup/formal
   work and append route expansion, repair, reopened, and replacement work so
   users do not see apparent progress rollback when the route is refined.

5. **Use normal repair for final-closure blocker combinations.** Missing final
   route-wide ledger, terminal replay, node acceptance plan, or node-context
   package evidence is still repairable through PM/runtime packets. Break-glass
   opens only when those normal lanes cannot produce a legal next action or the
   same root cause reaches the existing repeated-failure threshold.

6. **Strengthen the fake-AI universe before claiming coverage.** Observed live
   misses become seed profiles for ContractExhaustionMesh-style Cartesian
   families. Each generated cell must have an oracle and focused evidence owner:
   reject, reissue, normal repair, pass, or threshold break-glass.

## Risks / Trade-offs

- **Risk: Matrix size grows faster than routine tests can run.** -> Split
  canonical generation from focused child suites, and let TestMesh record owner
  commands and freshness instead of running every heavy path in every local pass.
- **Risk: Reviewer suggestion enforcement creates filler.** -> Prompt cards
  must require concrete higher-standard suggestions tied to checked scope; tests
  should reject empty lists, not judge semantic richness beyond contract shape.
- **Risk: Progress monotonicity could be mistaken for route authority.** ->
  Keep progress fields display-only and assert route/frontier files remain the
  source of truth.
- **Risk: Final-closure normal repair may hide real control-plane deadlocks.** ->
  Preserve the no-legal-next-action and fifth-repeat break-glass tests.
