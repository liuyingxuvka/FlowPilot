## Context

FlowPilot's current prompt and model surfaces already preserve source-intent language and separate runtime mechanics from PM, Reviewer, and FlowGuard semantic/process judgment. The observed miss is narrower than a runtime schema bug and broader than an image/source-access case: a concrete user deliverable was converted into an easier reachable-only inventory with honest missing-status rows, then passed because it did not pretend missing items were present.

The repair must therefore land in existing PM, Reviewer, FlowGuard operator, child-skill, fake-AI, and coverage surfaces. Runtime/router must stay mechanical and must not learn semantic keyword matching.

## Goals / Non-Goals

**Goals:**

- Make PM preserve the user's concrete deliverable, scope, quantity, quality, material/evidence, and prohibitions through root contract, route, node acceptance, material/research handling, final ledger, and closure.
- Make Reviewer actively compare PM and Worker results against the original user intent and block status-only, report-only, reachable-only, or honest-missing substitutions when they replace a required deliverable.
- Make child-skill guidance inherit the parent user-intent standard so a child skill cannot lower the target into its own weaker output.
- Make FlowGuard process/product models reject completion paths where the original target is claimed done after a downgraded substitute.
- Add generic bad-case coverage across finite deliverable classes in fake-AI replay, synthetic coverage, and model-test alignment.

**Non-Goals:**

- No new packet/result fields, ledgers, gates, roles, UI, aliases, compatibility branches, or fallback paths.
- No runtime semantic string matching or keyword rejection.
- No image, VPN, or source-locator-specific prompt rule. Those may appear only as example fixtures if needed.
- No Reviewer authority to directly repair production artifacts. Reviewer may run checks, add review-scope tests or fixtures, and return blockers or PM suggestion items.

## Decisions

1. **Use existing prompt cards rather than adding a new stage.**

   PM and Reviewer already own the semantic quality boundary. The change strengthens their current obligations in startup intake, root contract, route skeleton, node acceptance, material/research, child-skill, package review, final replay, and closure cards.

2. **Use existing blocker and suggestion fields.**

   A missing required deliverable, inaccessible required material, unmet quantity, or unverified proof remains a normal blocker using existing `blockers` and `recommended_resolution`. Higher-standard but nonblocking improvements remain `pm_suggestion_items`.

3. **Keep runtime/router mechanical.**

   Runtime rejects stale packets, duplicate results, missing fields, wrong leases, and unsupported shapes. It does not decide whether "reachable-only" is semantically sufficient. Tests must assert that the runtime does not gain non-downgrade semantic terms.

4. **Represent examples as finite bad-case profiles.**

   The image/source-access case becomes one member of a generic family: deliverable replaced by status report. Other members cover tests, data processing, documents, UI/product output, code repair, and child-skill output.

5. **Bind model and test evidence together.**

   Card text alone is not enough. The change must add fake-AI profiles, synthetic coverage rows, and model-test alignment rows so the bad chain is replayed and cannot be claimed covered only by prose.

## Risks / Trade-offs

- [Risk] Prompt text becomes too broad and makes Reviewer overblock ordinary honest uncertainty. -> Mitigation: distinguish hard user-intent failures from nonblocking quality suggestions, and keep soft improvements in `pm_suggestion_items`.
- [Risk] The fix becomes overfit to the known image/source-access miss. -> Mitigation: use generic prompt wording and cover multiple deliverable classes in tests.
- [Risk] Semantic responsibility leaks into runtime. -> Mitigation: add negative card/runtime tests that forbidden semantic wording stays out of runtime code.
- [Risk] Coverage claims become too broad for synthetic tests. -> Mitigation: mark synthetic traces as non-live evidence and rely on model-test alignment plus focused tests for current contract coverage.
