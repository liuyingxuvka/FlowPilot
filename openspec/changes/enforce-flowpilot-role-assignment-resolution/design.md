## Context

The current runtime now records `role_continuity` and correctly reuses a
same-responsibility role once the slot exists. The remaining gap is earlier in
the control surface: Controller-facing next actions and recovery commands still
ask for `lease-agent --agent-id <new-agent-id>`. A host can therefore create a
fresh role chat before the runtime rejects that candidate and assigns the
packet to the existing same-responsibility role.

FlowPilot's new-only rule requires one structured current path. The fix must
not keep an old "open a fresh role then reject it" edge as a tolerated
compatibility surface.

## Goals / Non-Goals

**Goals:**

- Resolve role assignment before any new role surface is opened.
- Reuse current-run same-responsibility role ids without requiring Controller
  to supply a fresh candidate id.
- Permit new role creation only after the runtime explicitly authorizes it.
- Block missing role-continuity hydration when same-responsibility lease
  history exists in the current run.
- Keep sealed packet and result bodies hidden from Controller.

**Non-Goals:**

- Do not revive old router role-binding records as current authority.
- Do not infer prior-run role ids as reusable current-run roles.
- Do not change role output contracts or sealed body access.
- Do not add a compatibility alias that accepts both old and new public flows
  as equally valid.

## Decisions

### Decision: Add Resolve-First Assignment

Add a runtime-owned role-assignment resolution operation. It takes the current
packet and responsibility, checks the current-run role slot and current-run
lease history, and returns exactly one disposition:

- `reuse_existing_role`: Controller must deliver the handoff to the existing
  agent id; no new role surface should be opened.
- `create_new_role`: Controller may open a new role surface and then commit the
  lease with the authorized assignment token.
- `blocked`: Controller must not create a role surface; the runtime names the
  current blocker and required recovery action.

This makes "create new chat" a consequence of runtime resolution, not an input
to resolution.

### Decision: Make Lease Commit Consume An Authorized Assignment

The public `lease-agent` command becomes a commit step. It accepts an
assignment id produced by the resolve step, and it records the effective agent
id already authorized by that assignment. A raw fresh `--agent-id` is not the
normal public control path.

### Decision: Hydrate Or Block Missing Slots

If a role slot is missing but the current run has previous same-responsibility
leases, the resolver does not silently initialize a fresh role. It either
hydrates a reusable slot from public current-run lease metadata or blocks with a
role-continuity recovery reason. It never promotes prior-run or old-router
history into current authority.

### Decision: Keep Existing Reuse Memory Semantics

Replacement memory remains metadata-only and role-visible through
`open-packet`. The resolver may expose the assignment disposition and public
agent id, but not sealed packet or result bodies.

## Risks / Trade-offs

- [Risk] Existing CLI callers still use `lease-agent --agent-id`.
  -> Mitigation: fail those calls with an explicit current-contract error and
  point to `resolve-role-assignment`.
- [Risk] Active runs created before role-continuity slots exist could stall.
  -> Mitigation: hydrate only from same-run public lease metadata when possible;
  otherwise block with an explicit recovery disposition instead of silently
  creating a replacement.
- [Risk] The controller might ignore a reuse disposition and still open a new
  chat.
  -> Mitigation: next actions and recovery commands no longer ask for a fresh
  agent id when reuse is available, and tests assert that no `<new-agent-id>`
  placeholder appears in those commands.
