# Implementation Plan

## Phase 1: Repository Shape

Status: implemented.

- Keep the project public-ready.
- Remove machine-specific paths before publication.
- Keep docs English-first.
- Preserve the validated simulations as regression checks.

## Phase 2: Skill Draft

Status: implemented.

- Complete `skills/flowpilot/SKILL.md`.
- Document trigger conditions.
- Document that run modes are retired; startup asks only background-agent,
  scheduled-continuation, and display-surface questions.
- Document that formal FlowPilot routes start at showcase-grade scope and do
  not have a lower default tier.
- Document visible self-interrogation, host-probed continuation with
  manual-resume fallback, FlowGuard process design, and completion-time
  high-value review.
- Document hard safety gates.
- Document `.flowpilot/` lifecycle.

## Phase 3: Templates

Status: implemented.

- Finalize `.flowpilot/` template files.
- Include route, continuation/heartbeat, checkpoint, experiment, and capability
  evidence templates.
- Keep JSON canonical and Markdown derived.

## Phase 4: Scripts

Status: implemented.

- `scripts/check_install.py`: verify FlowGuard and expected skill/document
  layout.
- `scripts/smoke_autopilot.py`: run simulation smoke checks.

## Phase 5: Skill Validation

Status: run before and after implementation; rerun after future changes.

- Run both FlowGuard simulations.
- Run install/self-check scripts.
- Review docs for public/private boundary issues.
- Confirm completion self-interrogation cannot reuse old implementation
  evidence after standards are raised.

## Phase 6: Example

Status: implemented.

The minimal adoption example lives in `examples/minimal/`.

## Phase 7: Protocol Hard-Standard Governance

Status: active for ongoing FlowPilot changes.

Hard standards that future patches should preserve:

- Completion is task completion, not UI completion. A visible cockpit or chat
  view may project status, but completion must be derived from the active
  route/state/frontier/ledger, node completion ledger updates, and final
  backward replay.
- The controller/router is envelope-only. It may route packets, receipts,
  hashes, and status metadata, but it must not read sealed packet/result bodies,
  originate project evidence, or make PM/reviewer/worker decisions.
- When the controller has no legal next action, it must fail closed by writing a
  PM decision-required blocker instead of doing project work itself.
- PM owns route activation, route mutation, repair decisions, and task
  completion decisions. Reviewer gates remain responsible for independent
  pass/block evidence before PM completion.
- Workers can modify project artifacts only under a current-node packet scope
  and write grant. Result relay still requires packet/result ledger absorption
  and role identity checks.
- The active run has one canonical route/state/frontier/ledger source. Shadow
  drafts, stale route files, historical runs, or display snapshots cannot become
  current authority.
- Final reports should distinguish FlowPilot-completable route work from
  residual human inspection notes. Human inspection notes belong in the final
  report and should not leave otherwise-completed route nodes artificially open.

Soft checks that may be simplified when they create mechanical friction:

- Exact phrase or event-name matching may be replaced by normalized predicates
  when the protected control fact is unchanged.
- Redundant UI/display fields, duplicate "source" labels, or evidence-table
  presentation details should not be hard gates unless they protect canonical
  route/state/frontier/ledger authority.
- Micro-ordering checks between informational cards should be removed or
  softened when they do not protect role isolation, write grants, ledger
  identity, active-run authority, or completion truth.

Any change that relaxes soft checks must update the relevant FlowGuard model
and keep the hard-standard counterexamples failing before production protocol
or router code is changed.

Legal-wait convergence:

- Router-loop modeling uses an explicit role-event contract table. Each
  contract names prerequisite state and the event state that satisfies it.
- The model automatically generates no-next-action/blocker hazards for every
  reachable unsatisfied legal wait, so future event additions do not depend on a
  hand-written phase-specific wait list.
- Runtime waiting should be derived from router event metadata, especially
  `EXTERNAL_EVENTS.requires_flag`, plus the event flag that closes the contract.
