---
name: autonomous-concept-ui-redesign
description: Experimental opt-in orchestration skill for autonomous end-to-end UI redesign work. Use only when the user explicitly asks for autonomous-concept-ui-redesign, an experimental autonomous UI redesign pipeline, or when FlowPilot explicitly selects this strategy. It combines concept-led product/design framing, conditional FlowGuard UI Flow Structure modeling, image-based concept exploration with concept diagnosis/refinement, final concept evaluation packages, frontend-design implementation, design-iterator refinement, design-implementation-reviewer deviation review, and geometry/screenshot QA without optional user check-ins.
---

# Autonomous Concept UI Redesign

## Scope

This is an experimental non-interactive UI redesign orchestrator. It does not
depend on `concept-led-ui-redesign`. The concept-led product and design
discipline is built into this skill through its own references, then composed
with implementation, iteration, deviation review, app-icon realization, and
layout QA skills.

Use this skill only when explicitly selected. For ordinary UI work, let the
normal skill trigger rules apply.

## Built-In References And Companion Skills

Use the built-in references for concept-led framing and QA. Use companion
skills only when the corresponding phase starts, loading their `SKILL.md`
bodies progressively rather than copying their instructions here.

- Built-in references:
  - `references/functional-framing.md`: product job, user task, display element
    draft/review, FlowGuard model inputs, information architecture, content
    pressure, duplicate-information/control review, and QA implications.
  - `references/concept-brief.md`: concept prompt contract, visual anchors,
    color/effect contract, app/software icon direction, selected concept
    three-layer review, and concept refinement before coding.
  - `references/design-search.md`: first-round candidates, concept diagnosis,
    scoring, second-round synthesis, readiness checks, final concept
    evaluation package, and final concept selection.
  - `references/visual-qa-loop.md`: real UI screenshot, pointer walkthrough,
    content/localization, asset, motion, and completion QA.
  - `references/divergence-review.md`: concept-vs-implementation difference
    classification and loop closure.
  - `references/platform-notes.md`: desktop, high-DPI, canvas, slide, and
    other non-standard rendering surfaces.
  - `references/run-report-template.md`: final reporting, including
    FlowGuard gate status, structure contract, and skipped or unresolved model
    states.
- Companion skills:
  - `flowguard-ui-flow-structure`: conditional model-first UI interaction
    structure gate before concept or implementation work.
  - `imagegen`: bitmap concept and icon candidates when concept search is
    needed.
  - `frontend-design`: implementation and first rendered visual sanity pass.
  - `design-iterator`: bounded screenshot-analyze-fix loops after first render.
  - `design-implementation-reviewer`: deviation review against Figma, selected
    concept images, screenshots, or explicit visual baselines.

See `references/dependency-map.md` before the first run or when a dependency is
missing.

## Autonomy Rules

This pipeline is non-interactive by default.

- Do not ask optional design-preference questions.
- Do not ask whether to continue iteration.
- Do not ask whether to use a sibling skill.
- Make conservative defaults and record them as assumptions.
- Stop only for true blockers: app cannot run, required files are missing,
  mutually inconsistent requirements cannot be reconciled, destructive action is
  needed, protected credentials/login/payment are required, or no verifiable UI
  surface exists.

Default choices:

- Unknown design system: follow the existing UI conservatively.
- No Figma: skip Figma-specific comparison and use concept image, prior
  screenshot, current UI, or written design contract as baseline.
- No concept need: skip imagegen and use a written design contract.
- No FlowGuard structure risk: skip the FlowGuard UI Structure Gate only with a
  recorded reason when the task is visual-only and does not alter workflow,
  state, hierarchy, controls, overlays, navigation, or display ownership.
- No user-specified iteration count: run 10 design-iterator rounds, maximum 20.
- No user aesthetic preference: prioritize readability, information density,
  stable layout, low overlap risk, and consistency with the product.
- No user-specified palette: select one explicit accent color by default and
  name its purpose, allowed locations, intensity, and hierarchy role. Use a
  no-accent UI only when the user explicitly asks, the existing design system
  is clearly neutral-only, or a named product reason makes neutral-only safer.
- Concept search default: treat generated concept images as editable design
  hypotheses, not finished instructions. Diagnose function gaps, overload,
  fake features, unclear states, and implementation risks before selecting or
  coding from a concept.
- App/software icon scope: when the product surface is a desktop app, mobile
  app, packaged web app, or branded software artifact, treat the app icon as a
  product identity asset, not an in-UI decoration. Select or create one final
  icon source and plan how it becomes the real application icon.
- Competitor research: skip unless explicitly requested or required by the
  route.

## Workflow

### 1. Classify The Route

Choose one route and record why.

- `minor_ui_fix`: small layout, clipping, overlap, responsiveness, or polish
  task. Skip concept search unless requested.
- `concept_redesign`: fuzzy direction, large redesign, new visual language,
  major screen rebuild, app icon, or first-principles information architecture.
- `figma_implementation`: Figma/design file is the source of truth.
- `baseline_alignment`: user provided screenshot, current UI, or existing
  implementation as the target.

### 2. Product And Design Contract

For `concept_redesign`, perform the built-in concept-led gates:

- product inspection;
- functional goals, user task, workflow, decision points, required data,
  actions, states, and non-goals;
- display element draft and necessity review;
- information architecture, region priority, interaction intent, presentation
  mode, and content pressure;
- window/viewport contract;
- palette contract;
- default accent color contract;
- visual fidelity contract;
- design language that serves the information architecture;
- FlowGuard UI Structure Gate preparation: record the candidate controls,
  displayed information, UI states, navigation paths, overlay states,
  duplicate/redundant information candidates, duplicate same-level controls,
  and known model boundaries that the gate must accept, reject, or skip.
- concept brief derived from functional framing and design language;
- mandatory first-round candidate search when a substantial concept-led
  redesign is in scope;
- candidate scoring, concept diagnosis, second-round synthesis, concept
  refinement, and final concept/app-icon set selection;
- final concept evaluation package covering retained functions, removed
  extras, information hierarchy, layout zones, color roles, background and
  foreground treatment, accent/status colors, typography, spacing, surface
  language, interaction states, and implementation constraints;
- concept readiness gate: final concept version must account for required
  workflows, approved display elements, states, density, non-goals, and known
  implementation constraints before coding starts;
- selected concept three-layer gate before coding;
- selected app/software icon gate when applicable.

Read `references/functional-framing.md` before choosing aesthetic direction or
generating concept images. Read `references/concept-brief.md` and
`references/design-search.md` before using `imagegen` for concept or app-icon
candidates.

Do not treat the first selected concept as only a broad visual direction. If a
candidate has too many features, hides required controls, invents workflows,
uses an unsuitable density, or cannot express real states, revise the brief,
generate a refined concept version, or discard the candidate before
implementation. The implementation brief should name the final accepted concept
version and the concept elements that were explicitly removed, simplified, or
deferred.

For smaller routes, write a compact contract instead:

- target surface and user task;
- must-keep content/actions;
- visual direction or baseline;
- supported viewport/window sizes;
- explicit non-goals.

### 2.5 FlowGuard UI Structure Gate

Use `flowguard-ui-flow-structure` after product/design framing and before
concept brief, imagegen, Figma translation, or frontend implementation when the
surface has meaningful UI behavior or structure risk.

Trigger the gate when any of these are true:

- the route is `concept_redesign` and the surface has multiple states,
  controls, menu levels, panels, overlays, or navigation paths;
- the route is `figma_implementation` or `baseline_alignment` and the work
  changes controls, state flow, displayed information, hierarchy, overlays, or
  navigation;
- the user mentions duplicate information, duplicate buttons, conflicting
  controls, unclear parent/child hierarchy, unstable toolbars, menus, workflow
  completeness, or FlowGuard;
- implementation or iteration later changes controls, states, displayed
  information, navigation, overlays, or hierarchy enough to invalidate the
  existing structure contract.

Skip the gate only when the task is visual-only: spacing, color, typography,
copy, icon polish, or small alignment work with no workflow, state, hierarchy,
control, overlay, navigation, or display-ownership impact. Record the skip
reason in the run notes and final verdict.

When triggered, verify the real FlowGuard package before claiming FlowGuard
use, then build or review:

- a UI interaction model: initial state, states, controls, displayed
  information, events, transitions, availability, failure/recovery states,
  terminal states, validation boundaries, and rationale;
- duplicate information and duplicate same-level control review, with
  intentional redundancy allowed only when recorded as accessibility,
  persistent context, summary plus detail, or alternate user vocabulary;
- a model-derived UI structure contract: parent/child topology, persistent
  global regions, contextual second-level regions, local third-level controls,
  stable placement, navigation ownership, event/control ownership, display
  ownership, overlay hierarchy, validation boundaries, and unresolved states.

Do not continue to visual concept selection or frontend implementation if the
required UI behavior is too vague to model without inventing product behavior.
Mark the run `partial` or `blocked` with the missing behavior instead.

Carry the FlowGuard structure contract into:

- the concept brief and final concept evaluation package;
- the `frontend-design` implementation brief;
- design-iterator checks whenever screenshots reveal structural drift;
- design-implementation-reviewer deviation review;
- geometry QA for modeled states, stable regions, overlays, and control
  ownership;
- the final verdict.

FlowGuard owns behavior topology, hierarchy, stable placement, information
ownership, and redundancy review. It does not choose brand style, palette,
typography, bitmap concept art, or frontend implementation details.

### 3. Implementation

Load `frontend-design` and implement from the contract. Pass these inputs
explicitly in the work brief:

- target files or components;
- design system findings;
- content plan and layout zones;
- FlowGuard structure contract or recorded FlowGuard skip reason;
- visual direction or concept target;
- final concept evaluation package, including function, hierarchy, color,
  background/foreground, accent/status, typography, spacing, and accepted
  simplifications to reuse during screenshot comparison;
- final app/software icon target and required runtime/package bindings when
  applicable;
- interaction states;
- model-derived control/display ownership, hierarchy, stable placement,
  overlays, and redundancy decisions when the FlowGuard gate ran;
- viewport/window contract;
- non-goals and preserved behavior;
- verification expectations.

The implementation phase must produce a first rendered screenshot or record why
rendering is blocked.

For native desktop surfaces, such as Qt/PySide, Electron, Tk, WinUI, SwiftUI,
Compose, or Flutter desktop apps, do not treat an offscreen/headless screenshot
as automatically trustworthy visual evidence. Check that text, icons, window
chrome, scaling, and transparency render like the real platform. If offscreen
capture shows missing glyphs, unreadable text, wrong font fallback, blank
widgets, clipped chrome, or other renderer artifacts, capture from the real
desktop platform or record the screenshot evidence as `partial`/`blocked`.

### 3.5 App Icon Realization

Run this gate whenever the target is a desktop app, mobile app, packaged web
app, browser extension, installable tool, or other branded software artifact.

In-app display of an icon, logo, badge, or concept preview is not enough. The
selected app/software icon target must be realized as the real application
identity wherever the platform supports it:

- runtime window/application icon;
- taskbar/dock/shelf icon, including Windows AppUserModelID or equivalent when
  needed for the taskbar to show the app identity instead of the host runtime;
- tray/menu-bar icon when the app has tray or menu-bar presence;
- packaged executable, shortcut, installer, manifest, or bundle icon when
  packaging is in scope;
- in-app brand mark only when the product also intentionally shows the same
  mark inside the UI.

Use one canonical icon source or an explicitly recorded derivative chain so the
in-UI mark, window icon, taskbar icon, tray icon, and package icon cannot drift.
If packaging is out of scope, still bind and verify the runtime window/taskbar
or tray icon where the local app can expose it, and record the package-icon gap
as a remaining risk instead of silently passing.

This gate must record:

- selected icon source path or generation record;
- all generated/exported icon files and sizes;
- platform bindings attempted;
- screenshot, OS/runtime probe, manifest check, or package metadata evidence;
- any places where the platform still shows a host runtime icon;
- whether the same visual mark is used in UI, window, taskbar, tray, and
  package identity.

The final verdict is `partial` or `blocked` when an applicable app icon is only
shown inside the UI or concept image and not bound to the actual app identity.

When a transparent raster icon master exists, use
`scripts/app_icon_asset_check.py` when practical to check alpha/corner
transparency, preview small sizes, and export Windows `.ico` assets. The script
is mechanical evidence only; still review whether the icon is too dense,
card-like, text-heavy, or disconnected from the selected UI concept.

### 4. Iterative Refinement

Load `design-iterator` when any of these are true:

- first render has visible imbalance, clipping, crowding, poor hierarchy, or
  poor spacing;
- text overlaps or appears too small;
- the user requested strong polish;
- the route is `concept_redesign`;
- the first implementation materially diverges from the design contract.

Run a bounded loop:

- default 10 rounds;
- maximum 20 rounds unless FlowPilot explicitly raises the budget;
- one or two concrete changes per round;
- screenshot after each round;
- preserve working behavior and do not undo good prior changes.

If the problem is structural or the rendered UI exposes a weak concept target,
return to the FlowGuard structure contract, design contract, information
architecture, or concept refinement gate instead of repeatedly adjusting CSS.

If a refinement round materially changes controls, states, displayed
information, navigation, overlays, or hierarchy, re-run the FlowGuard gate or
record why the current model-derived structure contract remains valid.

During each refinement round for `concept_redesign`, compare the screenshot
against both the selected concept image and the final concept evaluation
package. Reuse the earlier concept judgments instead of re-litigating them:
required functions, removed extras, hierarchy, density, color roles,
background/foreground clarity, accent use, status colors, typography, spacing,
surface language, interaction states, and accepted implementation
simplifications.

### 5. Deviation Review

Load `design-implementation-reviewer` when a baseline exists:

- Figma node or design file;
- selected concept image;
- user-provided screenshot;
- prior accepted implementation screenshot;
- written visual fidelity contract.

Review layout, spacing, typography, color, state behavior, responsive behavior,
app/software icon realization, model-derived hierarchy/control/display
ownership when available, and accessibility-visible issues. Classify deviations
as accepted, fixed, or blocked. When Figma is unavailable, do not stop; use the
strongest available baseline.

Read `references/divergence-review.md` when the rendered UI materially differs
from the selected concept, authoritative reference, accepted screenshot, or
written visual contract. Compare visual style first, then functional/structural
fit, then presentation/readability/interaction clarity, then implementation
constraints.

For concept-led work, the deviation review baseline is not only the image. Use
the final concept evaluation package as the checklist for what the real UI must
match or intentionally simplify, especially color roles, background surfaces,
foreground text clarity, accent behavior, selected/hover/error/success colors,
and contrast.

### 6. Geometry And Screenshot QA

Run layout QA before final acceptance. Read `references/layout-geometry-qa.md`
when implementing this phase.

Minimum checks:

- text does not overflow its parent container;
- important controls are visible and reachable;
- no incoherent element overlap;
- no unintended horizontal scrolling;
- fixed headers/footers do not hide content;
- popovers, menus, dialogs, tooltips, and drawers stay in bounds;
- key states work at desktop, normal, compact, and any required mobile sizes;
- modeled FlowGuard states, stable regions, overlays, and control/display
  owners remain visible, reachable, or intentionally progressive;
- high-DPI or scaled Windows evidence includes logical size, physical pixels
  when available, and screenshot dimensions.
- applicable desktop/mobile/package app icons are visible in the real platform
  identity surface, not only inside the app content.
- native desktop screenshots identify whether they came from the real platform
  or an offscreen/headless renderer, and any renderer artifact is either fixed
  by recapture or recorded as `partial`/`blocked`.

Screenshots are required but not sufficient. Geometry evidence is the primary
anti-overlap proof; screenshot review is the visual sanity proof.

Read `references/visual-qa-loop.md` before declaring visual work complete. Read
`references/platform-notes.md` when web screenshot assumptions are weak,
especially desktop apps, canvas/custom drawing, slides, native widgets, or
high-DPI Windows captures.

### 6.5 Final Integrated Acceptance Gate

Before the final verdict, build a parent-owned final acceptance ledger. The
orchestrator owns this ledger; companion skills keep their own detailed
standards. Do not copy every child checklist into the final report, but do map
each applicable child-skill gate to evidence, freshness, status, and verdict
impact.

Ledger rows must cover the gates that applied to the run:

- FlowGuard UI structure gate: model evidence, structure contract, journey or
  scoped-coverage status when complete app-level UI coverage is claimed, UI
  text hierarchy blueprint, implementation validation when implemented/runnable
  UI completion is claimed, revalidation after structural drift,
  duplicate-information decisions, and duplicate-control decisions.
- concept framing/search/readiness: functional framing, display element review,
  candidate search or waiver, selected concept version, final concept
  evaluation package, rejected extras, and accepted simplifications.
- frontend implementation: files or components changed, preserved behavior,
  first rendered evidence, and known implementation constraints.
- design iteration: rounds run or justified skip, issues fixed, screenshot
  evidence, and any structural drift that required FlowGuard revalidation.
- deviation review: baseline, major deviations, accepted deviations, fixed
  deviations, model-derived hierarchy/control/display ownership alignment, and
  unresolved differences.
- functional walkthrough: changed and adjacent controls exercised, expected vs.
  actual result, pointer or keyboard reachability, and post-interaction
  evidence.
- geometry and screenshot QA: viewport/window sizes, screenshot trust,
  overflow/overlap/popup/fixed-region results, high-DPI notes, and modeled state
  coverage.
- content, localization, motion, assets, in-UI icons, and app/software icon
  realization when those surfaces are in scope.

Use only these ledger statuses:

- `pass`: current evidence satisfies the owning gate.
- `accepted_deviation`: a difference remains but has current evidence, a clear
  product/accessibility/content-density/design-system reason, and no weakening
  of the final user outcome.
- `skipped_with_reason`: the gate was not applicable or safely skipped for the
  route, with the reason recorded.
- `partial`: useful work exists but required evidence is missing, stale,
  untrusted, incomplete, or not strong enough for release confidence.
- `blocked`: a required gate failed or cannot be completed without a real
  blocker being resolved.

Hard downgrade rules:

- A final `pass` requires every triggered required gate to be `pass`,
  `accepted_deviation`, or `skipped_with_reason` with a valid route-specific
  reason.
- Reviewer output alone is not enough for final `pass` when FlowGuard,
  concept-readiness, functional walkthrough, geometry, screenshot, or app-icon
  evidence is required and missing.
- FlowGuard output alone is not enough for final `pass` when concept,
  implementation, screenshot, geometry, deviation-review, or app-icon evidence
  is required and missing.
- If the FlowGuard gate was triggered but the model, structure contract,
  duplicate/redundancy decisions, journey coverage for complete app-level UI
  claims, text hierarchy blueprint, implementation validation for
  implemented/runnable UI claims, or revalidation notes are missing or stale,
  the final status is `partial` or `blocked`.
- If rendered evidence is missing, untrusted, wrong-surface, stale, or shows
  unresolved overlap, clipping, unreachable controls, popup bounds failures, or
  hidden required controls, the final status is `partial` or `blocked`.
- If design iteration changes controls, states, displayed information,
  navigation, overlays, hierarchy, or app icon identity after earlier evidence,
  affected FlowGuard, deviation, functional, geometry, and screenshot evidence is
  stale until revalidated or explicitly scoped as unchanged.
- If an applicable app/software icon is only visible inside the UI and not bound
  to the real platform identity surface, the final status is `partial` or
  `blocked`.

### 7. Final Verdict

The orchestrator, not any sibling skill, decides completion.

Use `references/run-report-template.md` for the final report shape. The verdict
must state:

- route type;
- assumptions made instead of asking the user;
- concept mode used or skipped;
- concept diagnosis/refinement rounds and final accepted concept version;
- FlowGuard gate status, model id, structure contract summary, skip reason,
  revalidation notes, duplicate-information decisions, and duplicate-control
  decisions;
- final concept evaluation package and how it was reused during UI iteration;
- implementation scope;
- app/software icon target, binding evidence, and any package-icon gaps;
- design-iterator rounds and outcome;
- deviation review baseline and result;
- geometry QA result;
- final acceptance ledger result and any downgrade reasons;
- screenshot evidence;
- native desktop screenshot trust notes when applicable;
- remaining risks or skipped states;
- final status: `pass`, `partial`, or `blocked`.

Do not claim completion when the final acceptance ledger downgrades the run, or
when geometry QA, app-icon realization for applicable software artifacts, or
required rendered evidence is missing. If evidence cannot be produced, return
`partial` or `blocked` with the specific blocker.
