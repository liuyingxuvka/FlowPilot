## Context

FlowPilot already has runtime validators for current packet-result contracts and fake-AI rehearsals for canonical result bodies. The live `semantic_recheck` failure showed that this is not enough: a backend validator can know the required conditional fields while the AI-facing packet contract omits those fields from the finite menu or minimal valid shape. When the AI then submits a near-synonym or wrong-typed field, runtime may reject it, but the reissue packet must also provide enough correction information for the next fake-AI package to converge.

This change is test-focused. Production contract projection and runtime repair behavior may be implemented by the parallel `externalize-flowpilot-effective-result-contracts` work; this change adds the tests and coverage models that fail when those surfaces are incomplete.

## Goals / Non-Goals

**Goals:**

- Separate runtime validator coverage from AI-facing contract projection coverage.
- Cover every current result-contract finite option field and conditional profile field through a finite Cartesian matrix of packet family, condition, field path, projection surface, allowed values, and expected visible shape. `semantic_recheck.*` remains the representative runtime rehearsal path, not the whole coverage boundary.
- Cover rejection-to-retry convergence through bad fake-AI packages followed by corrected packages.
- Keep GlassBreak tests separate: normal recovery rows must converge before the fuse threshold, while dedicated threshold rows must still prove the fifth same-class repeat escalates.
- Register the new coverage in executable matrix, ContractExhaustionMesh, TestMesh, and Model-Test Alignment so parent confidence cannot ignore missing child rows.

**Non-Goals:**

- Do not add compatibility aliases or teach runtime to accept near-synonym fields.
- Do not change live AI prompting beyond what tests require from packet-local projection surfaces.
- Do not claim live AI semantic quality; fake-AI packages remain prepared control-plane evidence.
- Do not modify peer OpenSpec work under `externalize-flowpilot-effective-result-contracts`.

## Decisions

1. Treat projection and convergence as two different contracts.

   Runtime validation answers "will the backend reject a bad result?" Projection coverage answers "could the AI see the exact finite contract before writing the result?" Convergence coverage answers "does the runtime rejection packet contain enough current information for a legal retry?" Keeping these separate prevents a validator test from counting as AI usability evidence.

2. Model the finite boundary explicitly.

   The primary axes are packet family, conditional contract/profile, required field path, finite option field, forbidden alias, field type requirement, projection surface, mutation kind, retry count, and expected oracle. The concrete runtime rehearsal path is `flowguard_check.post_result` with blocker-bound `semantic_recheck_contract`, but the matrix itself must be data-driven from the current packet-result contract table and result-contract profile table so every finite option or exact profile field is covered without bespoke test logic.

3. Use bad-package fake AI modes instead of relying only on canonical fake bodies.

   Existing fake-AI helpers produce the exact correct `semantic_recheck` object. New tests must also submit deterministic misread payloads such as near-synonym fields, object-valued booleans, missing consumed read ids, and missing repair obligation ids. A corrected retry package must then use the reissue packet's correction surface.

4. Drive fake-AI rows from the packet-local contract surface.

   The deterministic responder reads `current_handoff_contract.required_report_contract`, `allowed_value_options`, `field_type_requirements`, `minimal_valid_shape`, and reissue-packet correction fields. It refuses to guess when finite options are missing, generates wrong-value rows for every visible finite option field, and proves that each row can be repaired from runtime's reissue packet before GlassBreak.

5. Keep production fixes out of the test change when possible.

   If a test currently fails because production projection is incomplete, the test should express that required behavior. Implementation details belong to the parallel contract externalization change unless the smallest local test helper adjustment is needed to exercise the public runtime surface.

## Risks / Trade-offs

- Projection matrix growth could make one test file unwieldy. Mitigation: put declarative case rows in small helpers and keep assertions focused by projection surface.
- Some new tests may initially fail until the parallel implementation change lands. Mitigation: keep test names and failure messages precise so the repair owner can fix the production surface directly.
- Background model checks can be slow. Mitigation: run targeted tests first, then start heavyweight model regressions through the repository's background artifact convention before final readiness claims.
- Fake-AI convergence tests can overclaim if they only inspect generated JSON. Mitigation: drive bad and corrected packages through real runtime submission and current-contract reissue paths.
