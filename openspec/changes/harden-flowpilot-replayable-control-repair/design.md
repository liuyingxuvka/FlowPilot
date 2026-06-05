## Context

FlowPilot already has a current-contract control plane, strict no-fallback
policy, and a Controller break-glass lane for development-mode control-plane
failures. The observed failure class is narrower: a generated evidence runner
can bind execution to a concrete FlowPilot packet/active phase, so a later
reviewer replay fails as a control-plane currentness error. PM can then choose
`stop_for_user`, but stopped-blocker recovery currently exposes PM reissue as a
normal recovery path.

## Goals / Non-Goals

**Goals:**

- Add a single shared instruction that package-produced scripts, checkers, and
  evidence generators remain replayable.
- Make reviewer replay targeted rather than default-all.
- Route replayability/package-control blockers to the existing Controller
  break-glass lane before user stop.
- Make PM `stop_for_user` a hard wait unless the user explicitly requests
  recovery.

**Non-Goals:**

- No legacy compatibility shims, old-field aliases, or fallback parsers.
- No broad new packet/result schema family.
- No new sealed-body authority for Controller outside the existing break-glass
  playbook.
- No automatic rerun of every script during review.

## Decisions

1. Use one shared package instruction instead of role-by-role duplication.

   The replayability rule belongs near packet-body construction or the common
   runtime card surface that every role sees. This keeps the repair small and
   avoids divergent role prompts.

2. Reuse Controller break-glass instead of adding a new recovery system.

   The repository already specifies a limited break-glass lane for FlowPilot
   control-plane failures. Replayability failures are a control-plane package
   problem, so PM guidance should route there before terminal/user stop.

3. Harden stopped-blocker recovery at the runtime boundary.

   Prompt wording alone is insufficient. When PM chooses `stop_for_user`, the
   public recovery command must not expose automatic PM reissue as a normal
   patrol/resume path. Reissue remains possible only through an explicit user
   recovery request.

4. Keep reviewer reruns optional and evidence-driven.

   Reviewers first inspect recorded run results for freshness, binding, and
   support. They rerun only when evidence is critical, suspicious, or needs
   adversarial replay.

## Risks / Trade-offs

- Prompt-only replayability guidance may not catch all future script authors.
  Mitigation: add a focused regression model/test that fails when a runner
  hard-requires a concrete active packet in replay context.
- Hardening `stop_for_user` can require an explicit user recovery command in
  cases where older flows auto-reissued PM repair packets. Mitigation: expose
  clear waiting state and reason rather than silently continuing.
- Break-glass must not become a general repair shortcut. Mitigation: reference
  the existing control-plane-only playbook and keep route/project work
  forbidden.
