## Context

FlowPilot already has strong current-contract rules: it rejects stale route
shapes, records route-wide evidence, and discourages compatibility shims. The
remaining gap is that a long-running route can still accumulate temporary
branches, fallback-like recovery paths, generated leftovers, or duplicate
maintenance code unless every phase asks the same structural question and
forces a disposition before closure.

This change affects planning prompts, packet/result templates, reviewer gates,
final ledger closure, and the FlowGuard planning-quality model. It must preserve
parallel peer work and avoid broad refactors outside the owned runtime surfaces.

## Goals / Non-Goals

**Goals:**

- Make route, node, packet, result, review, and final closure artifacts name the
  expected structure-hygiene outcome.
- Block unowned compatibility branches, fallback paths, duplicate adapters,
  stale generated artifacts, and unclear maintenance layers before done claims.
- Preserve allowed current-runtime recovery when it names the owner, current
  state, repair command, and validation evidence.
- Extend executable planning-quality coverage and focused tests for the new
  failure modes.
- Keep installation, topology, and validation evidence synchronized after the
  change.

**Non-Goals:**

- No new FlowPilot maintenance subsystem.
- No automatic migration from old route/result shapes into current completion
  evidence.
- No repo-wide cleanup, formatter pass, or refactor unrelated to structural
  convergence.
- No staging or reverting unrelated peer-agent changes.

## Decisions

1. Reuse existing phase gates instead of adding another manager.

   The PM route skeleton, node acceptance plan, worker packet/result pair,
   reviewer cards, evidence package, final ledger, and terminal closure already
   form the route's authority chain. Adding the structural convergence check at
   those points gives one clear ownership path and avoids a second authority
   that could drift.

2. Treat structure hygiene as a disposition, not a prose warning.

   Templates will ask for explicit dispositions: removed, rejected, retained as
   current-runtime recovery, retained as an owned maintenance layer, or blocked.
   This keeps legitimate maintenance layers possible while preventing silent
   recovery-branch accumulation.

3. Model the new hazards in planning quality.

   The FlowGuard planning-quality model will include negative scenarios for
   missing route-level review, missing node expectations, packet/result gaps,
   repair branches that keep compatibility paths, and final ledgers with
   unresolved structure debt. Tests will assert those hazards and the prompt
   surfaces that carry them.

4. Preserve negative rejection evidence.

   Evidence that an unsupported or stale path was rejected is allowed and useful
   when it is clearly marked as negative evidence. It must not be counted as a
   current completion path.

## Risks / Trade-offs

- [Risk] Extra fields could become checklist noise. -> Keep them short,
  disposition-oriented, and attached to existing PM/reviewer artifacts.
- [Risk] Workers might over-delete current safety recovery. -> The cards
  explicitly allow current-runtime recovery when ownership, state, repair, and
  validation evidence are named.
- [Risk] Prompt/template changes can drift from executable checks. -> Add
  FlowGuard planning-quality scenarios and focused unit tests that require the
  new surfaces.
- [Risk] Other agents may be editing shared logs or topology. -> Avoid staging
  unrelated changes, and only regenerate/record files that are required for this
  change after checking the working tree.

## Migration Plan

1. Add the OpenSpec delta and tasks.
2. Update FlowGuard planning-quality model/test coverage.
3. Update FlowPilot PM, worker, reviewer, evidence, ledger, and closure
   prompts/templates.
4. Run focused validations, then run heavyweight model regressions in the
   background contract directory.
5. Rebuild/check topology if the model/prompt/test surfaces changed.
6. Sync the installed FlowPilot skill, audit the install, and commit only owned
   files.

## Open Questions

None.
