---
name: autonomous-concept-ui-redesign
description: Experimental opt-in orchestration skill for autonomous end-to-end UI redesign work. Use only when the user explicitly asks for autonomous-concept-ui-redesign, an experimental autonomous UI redesign pipeline, or when FlowPilot explicitly selects this strategy. It combines concept-led product/design framing, image-based concept exploration, frontend-design implementation, design-iterator refinement, design-implementation-reviewer deviation review, and geometry/screenshot QA without optional user check-ins.
---

# Autonomous Concept UI Redesign

## Scope

This is an experimental non-interactive UI redesign orchestrator. It does not
replace `concept-led-ui-redesign`; it wraps that skill's front-end product and
concept discipline with implementation, iteration, deviation review, and layout
QA skills.

Use this skill only when explicitly selected. For ordinary UI work, let the
normal skill trigger rules apply.

## Required Sibling Skills

Use these sibling skills when the corresponding phase starts. Load their
`SKILL.md` bodies progressively rather than copying their instructions here.

- `concept-led-ui-redesign`: product inspection, functional framing, display
  element review, information architecture, concept search, and final UI target.
- `imagegen`: bitmap concept and icon candidates when concept search is needed.
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
- No user-specified iteration count: run 3 design-iterator rounds, maximum 5.
- No user aesthetic preference: prioritize readability, information density,
  stable layout, low overlap risk, and consistency with the product.
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

For `concept_redesign`, load `concept-led-ui-redesign` and perform the early
gates:

- product inspection;
- user task and workflow definition;
- display element draft and necessity review;
- information architecture;
- window/viewport contract;
- palette contract;
- visual fidelity contract;
- concept candidates and final target when concept search is warranted.

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
- interaction states;
- viewport/window contract;
- non-goals and preserved behavior;
- verification expectations.

The implementation phase must produce a first rendered screenshot or record why
rendering is blocked.

### 4. Iterative Refinement

Load `design-iterator` when any of these are true:

- first render has visible imbalance, clipping, crowding, poor hierarchy, or
  poor spacing;
- text overlaps or appears too small;
- the user requested strong polish;
- the route is `concept_redesign`;
- the first implementation materially diverges from the design contract.

Run a bounded loop:

- default 3 rounds;
- maximum 5 rounds unless FlowPilot explicitly raises the budget;
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
and accessibility-visible issues. Classify deviations as accepted, fixed, or
blocked. When Figma is unavailable, do not stop; use the strongest available
baseline.

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

Screenshots are required but not sufficient. Geometry evidence is the primary
anti-overlap proof; screenshot review is the visual sanity proof.

### 7. Final Verdict

The orchestrator, not any sibling skill, decides completion.

Use `references/run-report-template.md` for the final report shape. The verdict
must state:

- route type;
- assumptions made instead of asking the user;
- concept mode used or skipped;
- implementation scope;
- design-iterator rounds and outcome;
- deviation review baseline and result;
- geometry QA result;
- screenshot evidence;
- remaining risks or skipped states;
- final status: `pass`, `partial`, or `blocked`.

Do not claim completion when geometry QA or required rendered evidence is
missing. If evidence cannot be produced, return `partial` or `blocked` with the
specific blocker.
