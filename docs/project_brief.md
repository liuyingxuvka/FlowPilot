# Project Brief

## Name

`flowpilot`

## Goal

Create a Codex skill that can drive substantial software projects using a
showcase-grade, persistent, FlowGuard-designed and FlowGuard-validated
project-control protocol.

The skill should help an agent avoid:

- premature completion;
- target drift;
- unverified progress;
- hidden or shallow self-interrogation;
- heartbeat logs without real continuation;
- stale plans after new facts appear;
- completion while obvious high-value work remains;
- unmerged parallel work;
- UI work without rendered screenshot review;
- generated app icons or visual assets that do not match the UI style;
- infinite recovery loops.

## Primary Users

- AI coding agents that need to run large projects across long sessions;
- human supervisors who want reliable evidence of progress;
- future agents resuming from local files rather than chat context.

## Non-Goals for v1

- No standalone package manager.
- No mandatory graphical UI in the core skill.
- No vendored copy of the FlowGuard skill.
- No automatic external publishing.
- No attempt to replace all domain-specific skills.

FlowPilot may still install safe project-local tools and libraries during a run
when they are needed for checks or implementation and the action is recorded.

## v1 Deliverables

- `flowpilot` skill.
- `.flowpilot/` project-control templates.
- FlowGuard meta-control model template.
- FlowGuard capability-routing model template.
- Installation/self-check protocol.
- Smoke scripts.
- Visual Cockpit example particle for `.flowpilot/` progress.
- Public-ready README and documentation.
