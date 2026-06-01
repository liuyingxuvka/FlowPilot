## Context

The new FlowPilot runtime already has a current packet lifecycle in
`flowpilot_new.py` and `flowpilot_core_runtime`. Role handoffs use
run-scoped packets and current commands such as `ack`, `open-packet`, and
`submit-result`. At the same time, active-looking prompt assets still describe
older Router/runtime-kit behavior such as `flowpilot_runtime.py
submit-output-to-router`, Router daemon state, active-holder leases, and
template control files.

This change is intentionally cleanup-heavy: it removes legacy prompt authority
instead of preserving a compatibility layer.

## Goals / Non-Goals

**Goals:**

- Make the current role-facing prompt contract singular and explicit.
- Remove old FlowPilot command/control language from current prompt, card,
  template, and skill surfaces.
- Add tests that fail if old command/control language returns to current
  surfaces.
- Keep historical backups preserved but outside current prompt authority.
- Sync the installed local skill and local git state after validation.

**Non-Goals:**

- No migration or alias support for old FlowPilot inputs.
- No fallback wrapper that translates old role-output commands into new packet
  submissions.
- No deletion of preserved backup archives.
- No remote push, release, tag, or deploy.

## Decisions

1. Current prompt authority is `flowpilot_new.py` packet lifecycle wording.
   Any active instruction that says formal role output should use
   `flowpilot_runtime.py submit-output-to-router`, old Router daemon action
   state, or active-holder lease authority is removed or rewritten to the
   current packet path.

2. Runtime-kit cards are treated as current only when their content is fully
   current-contract. If a card or template exists only for an old Router path,
   it is removed from current manifests or rewritten so it cannot be loaded as
   current authority.

3. Forbidden-surface checks operate on current surfaces, not preserved backups.
   The scan covers installed skill source after sync so the user's active
   environment cannot retain stale prompt text.

4. OpenSpec and FlowGuard evidence are part of the change. The OpenSpec
   artifacts define requirements and implementation tasks; FlowGuard project
   audit, focused checks, install checks, and background regressions provide
   execution evidence.

## Risks / Trade-offs

- Removing old prompt language can break tests that still assert old Router
  output paths. Mitigation: update those tests to assert current packet
  authority and add explicit negative tests for old surfaces.
- Some old Router code may still exist for preserved diagnostics. Mitigation:
  validation distinguishes code implementation names from current prompt
  authority and bans old terms only in current-facing prompt/card/install
  surfaces.
- Background model regressions can take time. Mitigation: run heavyweight
  regressions with the repository background artifact contract and inspect
  exit/meta artifacts before using them as evidence.

## Migration Plan

1. Inventory old command/control terms in repository and installed skill
   prompt surfaces.
2. Remove or rewrite current prompt/card/template/skill surfaces to the new
   packet contract.
3. Add forbidden-surface tests and install checks.
4. Run focused checks, sync the installed skill, audit freshness, and run
   background regressions.
5. Rebuild/check project topology if prompt/test/install ownership surfaces
   changed.
6. Commit the scoped local change.
