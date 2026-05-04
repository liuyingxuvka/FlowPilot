---
name: autonomous-concept-ui-redesign
description: Experimental opt-in orchestration skill for autonomous end-to-end UI redesign work. Use only when the user explicitly asks for autonomous-concept-ui-redesign, an experimental autonomous UI redesign pipeline, or when FlowPilot explicitly selects this strategy. It combines concept-led product/design framing, image-based concept exploration, frontend-design implementation, design-iterator refinement, design-implementation-reviewer deviation review, and geometry/screenshot QA without optional user check-ins.
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
    draft/review, information architecture, content pressure, and QA
    implications.
  - `references/concept-brief.md`: concept prompt contract, visual anchors,
    app/software icon direction, and selected concept three-layer review.
  - `references/design-search.md`: first-round candidates, scoring,
    second-round synthesis, and final concept selection.
  - `references/visual-qa-loop.md`: real UI screenshot, pointer walkthrough,
    content/localization, asset, motion, and completion QA.
  - `references/divergence-review.md`: concept-vs-implementation difference
    classification and loop closure.
  - `references/platform-notes.md`: desktop, high-DPI, canvas, slide, and
    other non-standard rendering surfaces.
- Companion skills:
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
- No user-specified iteration count: run 10 design-iterator rounds, maximum 20.
- No user aesthetic preference: prioritize readability, information density,
  stable layout, low overlap risk, and consistency with the product.
- No user-specified palette: select one explicit accent color by default and
  name its purpose, allowed locations, intensity, and hierarchy role. Use a
  no-accent UI only when the user explicitly asks, the existing design system
  is clearly neutral-only, or a named product reason makes neutral-only safer.
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
- concept brief derived from functional framing and design language;
- mandatory first-round candidate search when a substantial concept-led
  redesign is in scope;
- candidate scoring, second-round synthesis, and final concept/app-icon set
  selection;
- selected concept three-layer gate before coding;
- selected app/software icon gate when applicable.

Read `references/functional-framing.md` before choosing aesthetic direction or
generating concept images. Read `references/concept-brief.md` and
`references/design-search.md` before using `imagegen` for concept or app-icon
candidates.

For smaller routes, write a compact contract instead:

- target surface and user task;
- must-keep content/actions;
- visual direction or baseline;
- supported viewport/window sizes;
- explicit non-goals.

### 3. Implementation

Load `frontend-design` and implement from the contract. Pass these inputs
explicitly in the work brief:

- target files or components;
- design system findings;
- content plan and layout zones;
- visual direction or concept target;
- final app/software icon target and required runtime/package bindings when
  applicable;
- interaction states;
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

If the problem is structural, return to the design contract or information
architecture instead of repeatedly adjusting CSS.

### 5. Deviation Review

Load `design-implementation-reviewer` when a baseline exists:

- Figma node or design file;
- selected concept image;
- user-provided screenshot;
- prior accepted implementation screenshot;
- written visual fidelity contract.

Review layout, spacing, typography, color, state behavior, responsive behavior,
app/software icon realization, and accessibility-visible issues. Classify
deviations as accepted, fixed, or blocked. When Figma is unavailable, do not
stop; use the strongest available baseline.

Read `references/divergence-review.md` when the rendered UI materially differs
from the selected concept, authoritative reference, accepted screenshot, or
written visual contract. Compare visual style first, then functional/structural
fit, then presentation/readability/interaction clarity, then implementation
constraints.

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

### 7. Final Verdict

The orchestrator, not any sibling skill, decides completion.

Use `references/run-report-template.md` for the final report shape. The verdict
must state:

- route type;
- assumptions made instead of asking the user;
- concept mode used or skipped;
- implementation scope;
- app/software icon target, binding evidence, and any package-icon gaps;
- design-iterator rounds and outcome;
- deviation review baseline and result;
- geometry QA result;
- screenshot evidence;
- native desktop screenshot trust notes when applicable;
- remaining risks or skipped states;
- final status: `pass`, `partial`, or `blocked`.

Do not claim completion when geometry QA, app-icon realization for applicable
software artifacts, or required rendered evidence is missing. If evidence cannot
be produced, return `partial` or `blocked` with the specific blocker.
