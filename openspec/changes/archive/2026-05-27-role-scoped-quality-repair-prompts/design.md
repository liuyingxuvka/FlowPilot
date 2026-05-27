## Context

FlowPilot now uses physical packet/result envelopes and role-isolated runtime
cards. The existing packet body and worker cards already require quality
evidence, proof of depth, and low-quality-success guards, while reviewer and
officer cards protect independent approval and modeling boundaries. The missing
piece is explicit role-scoped wording that tells executable workers to repair
in-scope defects before returning success without giving reviewer, officer,
Controller, or PM prompts silent execution authority.

The repository is under active parallel work. This change keeps implementation
limited to prompt/card text, a focused FlowGuard planning-quality boundary, and
focused tests so it can coexist with ongoing runtime refactors.

## Goals / Non-Goals

**Goals:**
- Make worker execution packets explicitly require self-check, in-scope defect
  repair, and re-verification before completion.
- Preserve reviewer independence by making review packets block or request
  repair instead of repairing reviewed artifacts.
- Preserve officer and PM authority boundaries by requiring report/model
  self-correction while routing target defects as findings, blockers, or PM
  suggestion items.
- Add executable model/test coverage so future prompt edits cannot reintroduce
  blanket direct-fix wording.
- Sync the installed local FlowPilot skill after source changes.

**Non-Goals:**
- Change packet runtime schemas, dispatch mechanics, route mutation behavior, or
  Controller execution policy.
- Grant reviewers, officers, Controller, or PM any new write authority over
  target artifacts.
- Publish, release, push, or merge changes.

## Decisions

1. Use role-scoped prompt variants instead of a global sentence.

   A global sentence is attractive because it is simple, but it would tell
   reviewers and officers to repair artifacts they are supposed to challenge or
   model. The implementation will place a concise execution-quality rule where
   PM authors executable worker packets and a separate authority-boundary rule
   where generic packet templates/cards can reach multiple roles.

2. Treat worker research/material-scan as evidence work, not default artifact
   repair.

   These packets can be assigned to worker roles, but their normal output is a
   report. They should fix report errors and missing evidence before returning,
   while target implementation defects remain PM-routed unless the packet's
   allowed writes explicitly authorize repair.

3. Keep repair-packet wording tied to explicit allowed reads/writes.

   Review-repair and Controller-repair packet flows already require bounded
   reads, writes, forbidden actions, and success evidence. The self-repair rule
   will reuse those boundaries rather than creating an open-ended "fix anything"
   obligation.

4. Verify with focused prompt-boundary checks first, then run broad regressions
   in the background.

   Focused tests should fail quickly if a role receives the wrong authority
   wording. Meta and capability checks are still useful broad evidence and will
   use the repository's background artifact contract.

## Risks / Trade-offs

- Reviewer role drift -> Mitigated by explicit anti-repair wording and tests
  that check reviewer cards keep repair as a blocker/request path.
- Overly narrow worker repair -> Mitigated by naming allowed scope, acceptance
  slice, write authority, and required evidence instead of only saying "check
  your work."
- Prompt duplication -> Mitigated by keeping canonical wording in packet
  templates and PM authoring cards, with worker/reviewer/officer cards carrying
  short role-level reminders.
- Parallel-work conflicts -> Mitigated by avoiding runtime refactor files and
  keeping this change to prompt/model/test surfaces.

## Migration Plan

1. Update prompt/card text with role-scoped quality-repair rules.
2. Update focused model/test coverage for inclusion and exclusion boundaries.
3. Run focused tests and FlowGuard planning-quality checks.
4. Sync the installed local FlowPilot skill and run install checks.
5. Launch broad Meta/Capability regressions in the background and inspect their
   artifact contract before reporting completion evidence.
