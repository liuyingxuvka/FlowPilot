## Context

FlowPilot stores a top-level `.flowpilot/current.json` pointer and run-scoped
state under `.flowpilot/runs/<run-id>/`. Recent parallel-run work made daemon
ticks run-scoped, but the foreground bootloader and human invocation semantics
still need an explicit boundary: a user saying "start FlowPilot" means "create
a new formal invocation," not "resume whichever run the current pointer names."

This matters because FlowPilot is designed to allow multiple independent runs.
An older `running` run can be valid history, a separate active workflow, or a
parallel workflow that should continue untouched. It must not become the target
of a fresh startup unless the user explicitly asks to resume it.

## Goals / Non-Goals

**Goals:**

- Fresh formal startup always creates a new run.
- Existing `running` runs remain independent and are not attached, stopped,
  merged, or superseded by fresh startup.
- Resume/continue behavior requires explicit user intent and a concrete target
  or target-selection flow.
- `current.json` remains UI focus/default-target metadata, not startup intent.
- Focused FlowGuard and runtime tests catch the exact regression observed in
  this chat.

**Non-Goals:**

- Do not change daemon per-run binding from the completed parallel-run work.
- Do not archive or rewrite older OpenSpec changes.
- Do not stop or clean up existing `.flowpilot/runs/*` records.
- Do not run the heavyweight Meta or Capability simulations for this scoped
  repair.
- Do not introduce a global singleton FlowPilot coordinator.

## Decisions

1. Fresh startup is an explicit intent, not a default attach.
   - The supported launcher path for formal startup uses `--new-invocation`.
   - Any code path handling that intent must allocate a fresh run shell before
     it reads current-run state for runtime authority.
   - Alternative considered: attach to an existing `running` pointer and ask
     after attach. Rejected because the attach itself can already deliver cards
     or mutate old-run state.

2. Resume is a separate intent.
   - A resume path may use `.flowpilot/current.json` as a default target only
     after the user explicitly asks to continue or resume.
   - Ambiguous resume targets should be surfaced for selection or blocked,
     rather than silently selecting a parallel run.
   - Alternative considered: infer resume from `current.status == running`.
     Rejected because parallel active runs are valid and do not represent user
     intent.

3. Parallel active runs are normal.
   - Fresh startup records or reports other active runs only as independent
     background context.
   - It must not stop, cancel, supersede, or import them unless a later route
     explicitly chooses to reference prior work as read-only evidence.

4. Tests should model the bootloader mistake directly.
   - Known-bad hazards include fresh startup with one old `running` pointer,
     fresh startup with multiple active runs, and missing `--new-invocation`.
   - Safe scenarios include explicit resume using a selected run id and fresh
     startup creating a new run while leaving existing runs untouched.

## Risks / Trade-offs

- Existing docs or prompts may still use "current run" loosely -> update the
  small launcher-facing wording that guides the assistant before daemon attach.
- Fresh startup can leave many active runs visible -> acceptable because
  FlowPilot intentionally supports parallel operation; cleanup remains an
  explicit lifecycle action.
- A user may actually want to resume but say "start" casually -> the safer
  default is new run; they can explicitly say "continue/resume" when needed.
- Meta/Capability checks are skipped -> focused startup/parallel-run FlowGuard
  checks plus runtime tests own this narrower risk boundary.
