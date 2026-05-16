## Context

FlowPilot currently has two related recovery surfaces:

- Heartbeat/manual resume loads current-run daemon state, controller ledgers,
  visible plan, crew memory, and then restores or replaces all six roles.
- Mid-run role liveness recovery restores or replaces affected roles and then
  runs Router-owned obligation replay before normal work resumes.

The implementation already opens a role-recovery transaction for
heartbeat/manual resume, but `_next_role_recovery_action` intentionally skips
heartbeat/manual trigger sources. The resume path writes a compatibility
`role_recovery_report` after `rehydrate_role_agents`, but that report currently
requires PM by default and does not run `role_recovery_obligation_replay`.

## Goals / Non-Goals

**Goals:**

- Keep heartbeat/manual resume responsible for daemon attach, current-run state
  load, visible plan restore, and all-six liveness/rehydration.
- After successful rehydration, let Router scan current-run obligations before
  PM resume decision.
- Settle valid existing ACK/output evidence, create durable replacement rows
  for missing obligations, and preserve original wait order.
- Mark PM resume decision as already satisfied only when replay completes
  without escalation.
- Preserve PM authority for semantic continuation, route mutation, acceptance
  changes, conflicting evidence, and unclear ownership.

**Non-Goals:**

- Do not change the mid-run `controller_reports_role_liveness_fault` recovery
  route except to keep it compatible with shared helper behavior.
- Do not let Controller or background roles read sealed packet/result bodies or
  infer progress from chat history.
- Do not change heartbeat cadence, daemon locking, patrol timer behavior, or
  startup question policy.
- Do not run heavyweight Meta or Capability simulations in this pass.

## Decisions

### Decision 1: Share replay, not the whole resume path

Heartbeat/manual resume keeps its own entry steps because it must attach to
the daemon and restore the run surface. Only the post-rehydration obligation
comparison converges with role recovery.

Alternative considered: route heartbeat/manual trigger sources through
`_next_role_recovery_action` directly. That would blur daemon attach and
resume-state duties with targeted liveness recovery and risks duplicate
Controller rows.

### Decision 2: Router compares jobs from ledgers

The comparison remains metadata-only and Router-owned. Router reads controller
action rows, scheduler rows, card return ledgers, packet ledgers, role recovery
reports, role generation/agent metadata, and output envelopes. Roles do not
choose old work from memory.

Alternative considered: ask rehydrated roles to report what they were doing.
That reintroduces chat-memory inference and makes stale agent output harder to
quarantine.

### Decision 3: PM is escalation, not default

After resume rehydration, PM is skipped only when replay can mechanically
settle or reissue all discovered obligations. PM remains required when replay
requires semantic judgement or cannot produce a legal next action.

Alternative considered: always ask PM after resume. That is safe but
unnecessarily serializes work the Router can prove from durable state.

## Risks / Trade-offs

- [Risk] Resume replay could duplicate work after valid output already exists.
  -> Mitigation: reuse current-run role/card/packet/contract/hash validation
  before replacement rows are created.
- [Risk] PM is skipped when semantic judgement is needed. -> Mitigation: model
  and runtime tests require PM escalation for ambiguity and route/acceptance
  drift.
- [Risk] Existing resume tests assume PM is always next. -> Mitigation: split
  tests into mechanical replay success and PM escalation cases.
- [Risk] Installed skill can drift from repo source. -> Mitigation: run
  repo-owned sync and install checks after validation.

## Migration Plan

1. Extend FlowGuard coverage so heartbeat/manual resume cannot finish role
   rehydration and immediately ask PM when mechanical replay is available.
2. Refactor Router implementation to reuse the role recovery obligation replay
   planner after `rehydrate_role_agents`.
3. Add runtime tests for resume replay settling existing evidence, reissuing
   missing work, and retaining PM escalation for ambiguity.
4. Run focused FlowGuard and pytest checks. Skip Meta/Capability per user
   instruction and record that skip.
5. Sync the repo-owned FlowPilot skill into the local installed skill and run
   install verification.
