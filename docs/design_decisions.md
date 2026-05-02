# Design Decisions

## Skill Boundary

`flowpilot` is a new orchestration skill, not a patch to the existing heartbeat
skill.

It uses heartbeat ideas, but its core identity is project autopilot:

- persistent state;
- route versions;
- model checks;
- capability routing;
- chunk verification;
- recovery and rollback.

## Default-On Startup

When FlowPilot is invoked, or when `.flowpilot/` exists, FlowPilot is enabled by
default. The controller should not first decide whether FlowPilot should exist.

A formal FlowPilot route is showcase-grade by default. There is no lower
quality tier for a formal FlowPilot run. For small maintenance work inside an
active project, FlowPilot may record continuity state, but it should not claim a
full formal route unless the showcase-grade gates ran.

The first user-facing startup gate is run-mode selection. If the host cannot
pause or the user asks to continue without selecting a mode, `full-auto` is
recorded as the fallback with a reason.

The mode prompt is displayed from loosest to strictest:
`full-auto`, `autonomous`, `guided`, `strict-gated`. `full-auto` is the
fallback default when no explicit selection is available, even though it is not
the loosest option.

Run modes change autonomy and hard-gate behavior, not the quality floor.

## FlowGuard Binding

The skill is strongly bound to real FlowGuard and the `model-first-function-flow`
skill.

If real FlowGuard cannot be imported, model-backed autopilot setup is blocked.

FlowGuard is both process designer and checker. New route structures,
capability routing, recovery branches, heartbeat behavior, and stateful target
logic should be modeled before dependent implementation. Counterexamples should
shape the design, not merely fail a final audit.

Initial route creation is recursive and model-backed. FlowPilot generates a
candidate route tree, freezes it only after a root FlowGuard review, and then
reruns FlowGuard at parent layers before entering child nodes. Route changes
use local re-simulation plus impact bubbling; the whole tree is re-modeled only
when the impact reaches the root or changes global contracts.

## Two-Layer Modeling

1. Meta-control model: how the agent drives the project.
2. Task-local model: how the target software behavior should work.

## `.flowpilot/` as Source of Truth

Chat context can help, but cross-thread recovery must use `.flowpilot/`.

Canonical files are machine-readable. Markdown is an English review view.

Until the desktop Cockpit is available, chat is also the temporary visible
cockpit. Route maps, node jumps, simulated next paths, checks, fallback exits,
heartbeat state, and acceptance deltas must be shown in the conversation rather
than hidden only in `.flowpilot/`.

## Capability Router

The autopilot should route to specialized skills through explicit gates. It is
a process controller, not a place to copy every downstream prompt.

Child-skill fidelity is a hard gate. When a capability declares a
`source_skill`, FlowPilot must read that skill's `SKILL.md`, load relevant
references or record why they were skipped, map the child workflow and
completion standard into route gates, and verify the resulting evidence before
the capability can close. This prevents FlowPilot from saying "use the UI
skill" or "use FlowGuard" while silently doing only a weaker shortcut.

Child-skill fidelity is not only instruction loading. FlowPilot also audits
step evidence against actual outputs, checks domain quality against the parent
node goal, and closes the child-skill iteration loop before returning control to
the parent route node. FlowPilot also projects key child-skill milestones as a
visible mini-route so the user can see the child skill's rhythm without copying
that skill's detailed prompt text.

Child-skill fidelity is PM-owned route design, not just execution hygiene. The
project manager extracts a gate manifest from the loaded child skill before
route modeling, assigns required approvers for every child-skill check, and
asks the reviewer plus both FlowGuard officers to review their slices before
PM route inclusion. Node entry refines the manifest for current context. The
main executor can draft evidence and implement, but cannot approve child-skill
gates or return the parent node from its own checklist pass.

## Quality Package

FlowPilot keeps route structure maintainable by adding one reusable quality
package instead of many repeated "raise the standard" stations.

The package runs at parent/module and node boundaries after focused grill-me
and before formal work. It records whether the current scope is too thin,
whether a low-risk high-value improvement exists, whether child-skill
milestones are visible, whether validation is strong enough, and whether
checkpoint closure would be rushed.

Improvement candidates are typed: small items stay in the current node, medium
items move to a later node, large items trigger route mutation and FlowGuard
recheck, and rejected items need a reason. This gives FlowPilot a way to raise
standards without repeatedly re-asking the same improvement question.

Before checkpoint or completion closure, anti-rough-finish review prevents a
verified but obviously thin result from being accepted as done. Final closure
also reconciles feature, acceptance, and quality-candidate matrices.

FlowPilot owns route state, evidence, order, recovery, and completion closure.
Child skills own domain execution details such as UI aesthetics, concept
generation, screenshot comparison method, icon generation, FlowGuard modeling
technique, and platform-specific implementation guidance. FlowPilot should
record that the child skill was invoked and completed to its own standard
rather than duplicating the child skill's prompt text.

Required early gate:

- showcase-grade floor;
- material intake before PM route design: the main executor writes a Material
  Intake Packet, the human-like reviewer approves sufficiency, and the project
  manager writes a material understanding memo with complexity classification
  and any discovery-subtree decision;
- visible full grill-me at formal boundaries, with at least 100 questions per
  active layer;
- focused grill-me at phase/group/module/leaf-node/child-skill boundaries,
  with 20-40 questions by default and up to 50 for complex boundaries;
- lightweight self-check at heartbeat/manual-resume micro-steps, with 5-10 targeted
  questions and no claim to satisfy a full or focused gate;
- layered full-round coverage across acceptance, functional capability,
  data/state, implementation strategy, UI/UX when relevant, validation,
  recovery/heartbeat, and delivery/showcase quality;
- visible route map before route execution and visible node roadmap before
  formal chunks;
- host continuation probe, then real heartbeat/watchdog/global-supervisor
  automation when supported or manual-resume evidence when unsupported;
- FlowGuard process design before route execution;
- quality package before formal chunks;
- anti-rough-finish and final matrix reviews before completion closure;
- completion self-interrogation before final close.

Conditional UI gates:

- route UI work to `concept-led-ui-redesign` when concept-led visual work is in
  scope;
- route UI polish and implementation guidance to `frontend-design` when
  applicable;
- record the child skill's concept-target/reference decision before
  implementation, including explicit waiver or blocker when applicable;
- record the child skill's rendered-QA and loop-closure evidence after
  implementation;
- include product-facing visual assets in the same UI child-skill evidence when
  they are created or changed;
- prevent post-implementation rendered QA evidence from being relabeled as
  pre-implementation concept evidence.

The first local Cockpit remains a showcase example and progress-view artifact,
not a global design specification for all FlowPilot-driven UIs.

## Persistent Crew And Workers

Formal FlowPilot routes now create or restore a fixed six-agent crew before
route work: project manager, human-like reviewer, process FlowGuard officer,
product FlowGuard officer, worker A, and worker B. The project manager owns
route, heartbeat-resume runway, PM stop signals, repair, and completion
decisions. The reviewer inspects; the FlowGuard officers own their models end
to end by authoring, running, interpreting, and approving or blocking them.
They do not implement product code.

The crew is persistent as six roles, not as guaranteed live subagent
processes. Heartbeat, sleep, manual resume, or host boundaries may make stored
subagent ids unavailable. FlowPilot therefore stores compact role memory
packets under `.flowpilot/crew_memory/` and treats them as the authoritative
recovery state. A resume may reuse a live agent when the host supports it, but
an unavailable role must be replaced from its latest memory packet before it
can approve or produce gate evidence. Raw chat transcripts are not the memory
source of truth.

Every PM resume or route-position decision must produce a completion-oriented
runway, not only a next gate. The main executor replaces the current visible
plan projection with that runway and keeps progressing until a PM stop signal,
hard gate, blocker, route mutation, or real execution limit stops it. Old PM
runways remain historical evidence rather than the current plan.

The visible plan projection must reach the host UI when the host exposes a
native plan/task-list tool. In Codex this means calling `update_plan` or the
equivalent native plan tool with the PM runway before work starts. A persisted
`.flowpilot` runway file is necessary evidence, but it is not a substitute for
the native plan call when the tool is available. If no native plan tool exists,
FlowPilot records that fallback explicitly and shows the runway in chat.

Worker lifecycle:

```text
project-manager node decision
-> child-node scan
-> no need, reuse worker A/B, or replace only when unrecoverable
-> bounded/disjoint sidecar task
-> report returned
-> main-agent merge and verification
-> worker returns to idle crew slot
```

Worker agents must not own child nodes, checkpoints, route advancement,
acceptance-floor changes, or completion. Returned sidecar work must be merged
and verified by the main executor, then the project manager decides the next
route movement.

After meaningful PM decisions, reviewer judgements, FlowGuard officer reports,
or worker sidecar reports, the role's report path and memory packet are both
updated before checkpoint. Terminal closure archives both the crew ledger and
role memory status after lifecycle reconciliation.
