## Context

FlowPilot already has strong normal repair paths: Router materializes
`control_blocker` records, PM chooses executable repair transactions, workers
and officers run bounded packets, reviewers recheck, and terminal closure
summarizes FlowPilot skill improvement observations. Controller is deliberately
limited: it relays envelopes, watches the daemon/action ledger, records
receipts, and must not read sealed bodies, approve gates, mutate routes, or do
target-project work.

That boundary is correct for ordinary project defects, but it can deadlock when
the broken component is the FlowPilot control channel itself. This design adds
a narrow development-mode escape hatch for those cases without weakening normal
role authority.

## Goals / Non-Goals

**Goals:**

- Give Controller a visible, repeated reminder that a break-glass path exists
  only when normal FlowPilot control flow itself is broken.
- Keep the full break-glass policy in a manifest-listed system playbook at
  `skills/flowpilot/assets/runtime_kit/cards/system/controller_break_glass_repair.md`.
- Record every break-glass incident and temporary patch in a run-scoped ledger
  under `.flowpilot/runs/<run-id>/controller_break_glass/`.
- Make the lane useful even when PM/packet/control-blocker routing is the
  broken path.
- Use FlowGuard to prove the lane does not become ordinary Controller self-work,
  gate approval, route mutation, sealed-body access, or untracked patching.

**Non-Goals:**

- No authority for Controller to repair target-project product code.
- No authority for Controller to approve gates, close nodes, mutate routes,
  change acceptance, read sealed packet/result bodies, publish, deploy, or touch
  secrets.
- No replacement for PM repair, worker reissue, reviewer recheck, or existing
  `controller_repair_work_packet` when those paths are available.
- No remote push or release.

## Decisions

1. **Use a two-layer prompt shape.**
   - Add a detailed system playbook card for the full policy.
   - Add a short reminder to repeated operational surfaces:
     `controller_table_prompt`, daemon status, patrol timer output, and
     `continuous_controller_standby` payload.
   - Rationale: a role-card-only instruction may be forgotten during a long
     foreground run, while a long reminder in every ledger row would encourage
     overuse.

2. **Keep break-glass outside normal Router repair transactions.**
   - Normal `control_blocker` and PM repair transactions remain default.
   - Break-glass is allowed only when the normal control repair lane is itself
     unavailable, contradictory, looping, or unable to produce a legal next
     action.
   - Rationale: using the broken PM/packet lane to repair the broken PM/packet
     lane can deadlock. The escape hatch must not depend on the mechanism it is
     diagnosing.

3. **Use run-scoped incident and patch ledgers.**
   - Incidents record trigger proof, normal-lane checks, suspected control-plane
     defect, allowed reads/writes, forbidden actions, and exit decision.
   - Patch records capture temporary file changes or compensation, validation,
     rollback command/notes, and final disposition.
   - Rationale: temporary repairs are acceptable only when they remain visible,
     auditable, and reversible.

4. **Model the authority boundary before trusting runtime behavior.**
   - Add a focused FlowGuard model/check for break-glass eligibility,
     forbidden powers, required records, and final reporting.
   - Rationale: this is a process/authority change. Prose-only rules are not
     enough.

5. **Do not make break-glass a hidden completion path.**
   - Break-glass may unblock the control plane, but normal route evidence must
     still pass through the correct route, review, and closure gates once the
     control channel is healthy again.

## Risks / Trade-offs

- **Controller overuses break-glass for ordinary project bugs** -> Mitigate
  with narrow eligibility checks, repeated "not for project bugs" reminders,
  and FlowGuard known-bad hazards.
- **Break-glass hides temporary patches** -> Mitigate with required incident
  and patch ledgers plus final skill-improvement reporting.
- **The reminder becomes noisy** -> Keep the repeated reminder short and point
  to the detailed playbook only when the control flow appears broken.
- **The lane bypasses PM/reviewer authority** -> Forbid gate approval, route
  mutation, acceptance changes, sealed-body access, and project evidence
  creation; require return to normal flow after control-plane recovery.
- **Concurrent agents edit nearby files** -> Keep edits focused and avoid
  structure-maintenance files already touched by active parallel work unless
  directly required.

## Migration Plan

1. Add the OpenSpec specs and focused FlowGuard break-glass model.
2. Add the Controller system playbook and manifest entry.
3. Add repeated reminder payloads to the Controller table prompt, daemon status,
   standby payload, and patrol timer output.
4. Add run-scoped incident/patch templates and schema docs.
5. Add focused runtime/card tests and install-check coverage.
6. Run focused checks, then sync the local installed FlowPilot skill.
7. Stage and commit only this change's files; do not stage unrelated parallel
   AI work.

Rollback is local: revert this change's files and remove installed copied
break-glass card/runtime outputs through the existing install sync after the
source revert. No remote rollback is needed.

## Open Questions

- None blocking implementation. If later evidence shows repeated use of
  break-glass, that should become a separate FlowPilot root-repo maintenance
  backlog item rather than expanding Controller authority in this change.
