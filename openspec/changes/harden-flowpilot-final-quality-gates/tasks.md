## 1. FlowGuard And Boundary Planning

- [x] 1.1 Record the FlowGuard route snapshot for this change: existing model
      boundary, DevelopmentProcessFlow order, Model-Test Alignment obligations,
      and TestMesh/background evidence plan.
- [x] 1.2 Audit current runtime final gate helpers and focused tests to identify
      the minimal current-contract code surfaces to touch.

## 2. Runtime Final-Gate Hardening

- [x] 2.1 Add runtime helper predicates for accepted review evidence, current
      FlowGuard proof, and passing validation evidence.
- [x] 2.2 Update final route-wide ledger and final requirement evidence matrix
      to use helper predicates instead of id presence.
- [x] 2.3 Update closure blockers to consume invalid final-quality evidence and
      keep blocked/stale/failed evidence unresolved.
- [x] 2.4 Update terminal backward replay result validation so submitted segment
      ids must match runtime-issued active-route targets exactly.

## 3. Prompt/Card Alignment

- [x] 3.1 Clarify existing final ledger, closure, and terminal replay cards only
      where needed to state that invalid evidence ids do not count as proof.

## 4. Tests And Model Alignment

- [x] 4.1 Add focused runtime tests for blocked review, stale FlowGuard, failed
      validation, historical route evidence, and terminal replay segment parity.
- [x] 4.2 Update or add FlowGuard/model-test alignment evidence for the new
      final-quality gate obligations.
- [x] 4.3 Run focused tests and FlowGuard checks; triage failures before broad
      validation.

## 5. Validation, Sync, And Closure

- [x] 5.1 Run required topology build/check and selected broader regressions,
      using background artifacts for heavyweight checks when appropriate.
- [x] 5.2 Run repository-owned install sync, install check, and installed
      freshness audit.
- [x] 5.3 Update adoption evidence, OpenSpec task status, KB postflight, and
      local git state without reverting peer work.
