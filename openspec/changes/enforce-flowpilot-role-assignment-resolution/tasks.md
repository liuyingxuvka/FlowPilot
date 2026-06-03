## 1. Contract And Routing

- [x] 1.1 Validate the OpenSpec change before implementation.
- [x] 1.2 Map current role dispatch, lease commit, and recovery command surfaces.
- [x] 1.3 Confirm the minimum FlowGuard revalidation route and background checks.

## 2. Runtime Assignment Resolution

- [x] 2.1 Add current-run role assignment records and events.
- [x] 2.2 Implement resolve-first role assignment with reuse/create/block dispositions.
- [x] 2.3 Hydrate missing role-continuity slots from current-run same-responsibility lease metadata or block.
- [x] 2.4 Make lease commit consume authorized assignments instead of raw fresh candidates.

## 3. Public Control Surface

- [x] 3.1 Replace Controller-facing `lease-agent --agent-id <new-agent-id>` next actions with resolve-first commands.
- [x] 3.2 Add a public command to resolve role assignment before role surface creation.
- [x] 3.3 Add a public commit command or tighten `lease-agent` so raw agent ids are rejected.
- [x] 3.4 Update handoff output to carry assignment provenance without exposing sealed bodies.

## 4. Tests And Evidence

- [x] 4.1 Add focused tests for reuse resolution without fresh candidate ids.
- [x] 4.2 Add focused tests for missing-slot hydration and missing-slot blockers.
- [x] 4.3 Add negative tests for raw `lease-agent --agent-id` current-contract rejection.
- [x] 4.4 Run focused runtime tests, compile checks, and OpenSpec validation.
- [x] 4.5 Run required FlowGuard/meta/capability regressions in background and inspect artifacts.

## 5. Sync And Finalization

- [x] 5.1 Sync installed local FlowPilot skill from the repository version.
- [x] 5.2 Run install freshness checks and local install audit.
- [x] 5.3 Rebuild/check topology if required by touched surfaces.
- [x] 5.4 Update FlowGuard adoption evidence and KB postflight.
- [x] 5.5 Commit the scoped local git changes without reverting peer-agent work.
