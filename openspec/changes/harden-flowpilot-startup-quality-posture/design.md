## Context

The current FlowPilot startup trunk is Runtime/Router mechanical startup
followed by PM first-round work through the sealed `user_intake` packet. Later
surfaces already carry strong standards: product-function architecture,
acceptance contract inheritance, PM route planning, node acceptance plans,
packet bodies, result matrices, and Reviewer active challenge.

The weak point is the bridge from startup release into the first PM artifacts.
If a role sees startup as only a mechanical clearance, the first route can set
a shallow semantic floor and later packets can faithfully inherit that weaker
floor.

## Goals / Non-Goals

**Goals:**

- Make a normal fresh FlowPilot startup project a high-quality current-run
  work posture before PM drafts product architecture or route structure.
- Carry that posture through existing PM, Reviewer, node acceptance, packet,
  and result prompts using existing text fields and templates.
- Add focused model/test coverage so prompt drift is caught before local
  install sync.
- Keep backend role prompts positive and direct: normal high-quality current
  work, concrete artifacts, acceptance evidence, and proof of depth.

**Non-Goals:**

- No new runtime state, schema fields, packet kinds, result fields, ledgers, or
  role types.
- No new launcher mode, alternate entry path, compatibility shim, fallback
  parser, or old-name alias.
- No child-skill body edits. Existing FlowPilot child-skill selection and Skill
  Standard Contract projection remain the owner of child-skill rigor.
- No role-facing wording that presents non-operational paths or mode choices
  as something a role should reason about.

## Decisions

1. Use positive prompt propagation instead of runtime branching.
   The repair belongs in existing prompt cards and templates because the
   observed issue is semantic quality posture, not mechanical validity.

2. Strengthen the startup-to-PM bridge first.
   `pm_startup_intake.md` and its decision template will state that startup
   release carries normal high-quality current-run work into PM product
   architecture and route planning.

3. Project the posture into existing downstream gates.
   Product architecture, route challenge, route skeleton, node acceptance, and
   packet/result templates will receive minimal wording that preserves the
   same quality floor without adding fields.

4. Keep non-operational vocabulary out of role-facing operational prompts.
   Dedicated tests and FlowGuard bad-case names may model forbidden variants,
   but startup, PM, Reviewer, Worker, and packet prompts should not present
   those variants to role agents.

5. Validate with focused checks before install sync.
   Update existing planning-quality and reviewer-quality checks plus runtime
   card reminder checks, then rerun targeted model and unit evidence before
   rebuilding topology and syncing the installed skill.

## Risks / Trade-offs

- [Risk] Prompt text becomes too broad and every small task looks huge.
  [Mitigation] Preserve existing simple-task/minimum-sufficient-complexity
  wording; require high quality within the current task boundary, not maximal
  bureaucracy.

- [Risk] A negative warning leaks non-operational mode labels into backend
  prompts.
  [Mitigation] Operational prompt edits use positive wording only; variant
  names stay in model/test artifacts.

- [Risk] Validation becomes another compatibility surface.
  [Mitigation] Tests assert current prompt markers and forbidden drift; they do
  not teach Runtime to accept alternate input shapes.

- [Risk] Parallel AI work changes nearby files after validation.
  [Mitigation] Keep touched files scoped, check git status before final claims,
  and rerun affected validation after edits.
