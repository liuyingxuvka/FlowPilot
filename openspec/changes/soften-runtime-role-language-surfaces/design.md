## Context

The previous role-binding change updated the core runtime language, but a
follow-up prompt audit found that old wording remains in UI copy, PM startup
activation checks, public protocol text, reference protocol reminders, and the
repository handoff. These surfaces are read by humans or future agents and can
therefore reintroduce historical assumptions even when executable runtime
contracts are already current.

## Goals / Non-Goals

**Goals:**

- Use positive, current-rule wording: FlowPilot may request additional role
  assistance when the current runtime responsibility needs it and the host
  supports it.
- Avoid negative historical reminders such as "do not use fixed six" in active
  prompts and user-facing copy.
- Keep evidence requirements explicit: current run, requested responsibility,
  addressable id, ACK/result path, sealed-body isolation, and blocked-role
  recovery when host support is absent.
- Preserve existing data fields where changing them would be a schema
  migration rather than prompt cleanup.

**Non-Goals:**

- Do not rename persisted fields such as `background_agents`,
  `crew_ledger`, `crew_memory`, `requires_host_spawn`, or `spawn_result`.
- Do not alter runtime topology, role authority, packet lifecycle, PM/reviewer
  gates, or sealed-body policies.
- Do not rewrite historical adoption logs, archived OpenSpec changes, or
  known-bad fixtures unless they are active prompt sources.

## Decisions

1. **Use softer product language in UI.** The startup toggle becomes runtime
   role assistance rather than background agents. Its description mentions
   requesting additional role bindings when needed by the current task.

2. **Use binding coverage instead of role counts.** PM startup activation checks
   the role bindings requested for the current run, same-task rehydration
   evidence, or explicit blocked-role recovery authorization.

3. **Keep internal schemas stable.** Field names that encode prior vocabulary
   stay in place for compatibility, while surrounding prompt and docs explain
   them through the current role-binding model.

4. **Keep reference wording role-recipient based.** Reference docs should say
   controller-to-recipient-role or addressed role binding, not sub-agent, when
   describing active packet handoff rules.

## Risks / Trade-offs

- **Risk:** UI wording becomes too vague and weakens host evidence.
  **Mitigation:** Keep "when the current task needs it" plus install/prompt
  checks that require runtime-requested binding language.

- **Risk:** Replacing schema field names would create broad churn.
  **Mitigation:** Leave schema identifiers alone and only adjust prompt,
  public guidance, and copy surfaces.

- **Risk:** Handoff historical decisions still contain old context.
  **Mitigation:** Update active handoff "current" wording while leaving
  historical logs and archived records intact.
