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
- Document run modes in loose-to-strict display order: `full-auto`,
  `autonomous`, `guided`, `strict-gated`.
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
