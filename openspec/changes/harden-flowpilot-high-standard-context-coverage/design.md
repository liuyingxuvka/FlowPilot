## Context

FlowPilot is a current-contract, prompt-driven runtime. The existing flow
already separates runtime/router mechanical validity from PM, Reviewer, and
FlowGuard semantic/process judgment. Recent changes strengthened source-intent
preservation, formal gate review, and contract projection, but the user's
reported miss remains possible: PM can produce a merely adequate route, and
Worker/Reviewer/FlowGuard can operate from a local work packet without
explicitly carrying the original user standard and PM's complete execution
intent.

The repair must follow current-contract discipline:

- no UI work;
- no fallback, compatibility alias, old-router recovery, or missing-field
  default;
- avoid new fields unless existing packet/result/gate fields cannot represent
  the requirement;
- keep runtime mechanical, not semantic;
- preserve peer work and install-sync evidence after prompt/runtime/test
  changes.

## Goals / Non-Goals

**Goals:**

- Make PM's first planning pass rich enough to define the highest reasonable
  product standard under the user's request and route scope.
- Ensure every backstage role can see and use the same current user/PM standard
  through existing fields, especially `relevant_references`,
  `acceptance_criteria`, `known_risks`, and acceptance-item projections.
- Require in-scope high-quality improvements from Workers and substantive
  challenge from Reviewers without letting either role silently change scope,
  route, acceptance, or authority.
- Extend existing runtime contract projection so required existing fields are
  present in fake-AI and Cartesian negative coverage.
- Prove the change with focused tests, FlowGuard models, topology checks, and
  install/local sync checks.

**Non-Goals:**

- No new UI, visual surface, or user-facing workflow.
- No runtime semantic scorer for whether a plan is "high standard enough."
- No new packet kind, role, ledger, route state family, or compatibility
  translation layer.
- No migration of historical artifacts or old field aliases into the current
  valid path.

## Decisions

1. Use existing context fields as the global-standard carrier.

   `node_context_package.relevant_references`, `acceptance_criteria`,
   `known_risks`, and acceptance-item projection are already current FlowPilot
   packet/result concepts. The prompt cards will require PM to fill them with
   root/user contract, product architecture, high-standard contract,
   acceptance-item registry, route-node, material, risk, and verification
   references. This avoids adding a new `global_context` field.

   Alternative considered: add a dedicated global-standard field. Rejected
   because the same information already belongs to existing packet context
   fields and adding a new field would create another authority surface.

2. Runtime blocks only mechanical existing-field failures.

   Runtime/router should reject missing required fields, empty arrays declared
   non-empty, wrong types, illegal enum values, forbidden old aliases, stale or
   cross-run identifiers, unsupported commands, and package/current-authority
   mismatches. Runtime should not reject a package for being semantically
   unambitious; Reviewer and FlowGuard own that challenge with existing
   blocker and repair fields.

   Alternative considered: add runtime checks for low-standard wording.
   Rejected because it would be brittle semantic judging in the wrong layer.

3. Worker/Reviewer authority is widened only inside existing scope.

   Workers should use the full user/PM standard and are expected to improve
   implementation quality when the improvement is inside the packet's writes,
   acceptance slice, verification scope, and authority. Reviewers should block
   source-intent loss, local-only packages, and low-standard artifacts. Both
   roles must escalate scope, route, acceptance, or authority changes instead
   of silently mutating the plan.

   Alternative considered: keep workers strictly literal to the local task.
   Rejected because it produces the observed low-standard completion behavior.

4. Coverage expands by Cartesian contract projection, not hand-picked examples.

   Existing fake-AI helpers and contract-exhaustion tests should enumerate every
   packet-result contract's required fields, required arrays, allowed values,
   forbidden aliases, and representative valid packages. Planning and
   node-context contracts receive focused cases because they are the source of
   the observed failure family.

   Alternative considered: add only a few prompt text assertions. Rejected
   because prompt-only coverage would not prove runtime projection or fake-AI
   package behavior.

## Risks / Trade-offs

- [Risk] Prompt text becomes broad but not enforceable. -> Mitigation: pair
  prompt-card tests with runtime contract projection tests and FlowGuard
  planning/replay models.
- [Risk] Runtime requiredness accidentally becomes semantic. -> Mitigation:
  keep contract changes limited to existing field presence/type/value/alias
  rules and add tests that Reviewer, not runtime, owns local-only quality
  challenge.
- [Risk] Node-context packages overfit one route shape. -> Mitigation: express
  requirements as current references and acceptance slices, not route-specific
  new fields.
- [Risk] Installation remains stale after repo edits. -> Mitigation: include
  install sync and audit checks in the verification contract before closure.

## Migration Plan

No data migration is planned. New behavior applies to current prompt cards,
current packet/result contracts, fake-AI fixtures, and tests. Historical old
packages remain unsupported unless they already satisfy the current contract.

## Open Questions

None for implementation. If later evidence shows an existing field cannot carry
one of the required references, that blocker must be raised explicitly before
adding a field.
