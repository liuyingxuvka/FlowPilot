# Visual QA Loop

Use this before claiming a UI redesign is complete.

## Baseline

1. Start the app or render the artifact through the normal local path.
2. Use realistic viewport or window sizes.
3. Verify the screenshot method captures the same UI the user would see. Do not treat a successful screenshot command as proof by itself.
4. Capture the main changed screen after render settles.
5. Capture important changed states, not only the default state.
6. Operate the changed and adjacent UI yourself. Do not ask the user to click through the interface for completion evidence.
7. After each material pointer interaction or state transition, capture evidence and inspect the new state before moving on.

## Functional Framing QA

Before judging beauty or polish, confirm the real UI still serves the functional framing:

- primary user job and main task are visible in the screen structure
- approved display elements are present, conditional, hidden, or removed according to the display element review
- no rejected display element was accidentally added back because it looked good in a concept image
- required content, data, actions, and states are present or deliberately deferred
- functional zones match the intended priority: primary work area, navigation, controls, details, feedback, and secondary context
- presentation mode fits the content pressure: table, cards, split panel, inspector, dashboard, timeline, canvas, form, or hybrid
- long labels, translations, dense data, and compact widths have not broken the intended structure
- non-goals and fake features from the concept were not accidentally implemented

Use this framing during the real UI three-layer review: style first, functional/structural fit second, presentation/readability/interaction third.

## Candidate Search QA

Before implementation evidence is accepted, confirm the selected concept came from the required search:

- at least three first-round candidate sets were generated
- first-round candidates were meaningfully different, not near-duplicate color tweaks
- each candidate was scored for function, display element value/load, interaction clarity, information presentation, aesthetics, app icon quality when applicable, and implementation feasibility
- second-round candidates were synthesized from the strongest first-round properties
- the final selection rationale considered all first- and second-round candidates
- app/software icon candidates were paired with UI candidates when the product needs an app icon

## Screenshot Method Gate

Before accepting any screenshot as visual evidence:

1. Identify the exact target: browser tab, native window, full desktop, slide page, canvas, or embedded host.
2. Read the relevant bounds before capture:
   - browser viewport for web-only QA
   - native window bounds for desktop-window QA
   - logical screen size, physical screen size, and working area for Windows desktop QA when available
3. Put the target in a known state: foreground, unoccluded, maximized or explicitly sized, render settled, and using the intended project/data source.
4. Save the screenshot and verify the saved image dimensions match the intended capture target.
5. Visually inspect the proof image for required boundaries:
   - full window screenshot: title bar/top edge, left and right edges, and bottom/status area are visible
   - full desktop screenshot: Windows taskbar or another desktop boundary is visible unless there is recorded evidence that it is hidden
   - browser screenshot: browser viewport contains the intended route/state, not a fallback page or wrong tab
6. Reject and recapture screenshots that show only a corner, crop the bottom/right side, capture the wrong foreground app, hide required desktop boundaries, blur high-DPI content, or use a browser preview as final proof for a desktop app.

On high-DPI Windows systems, logical APIs may report scaled sizes such as 1280x720 while the physical screen is 3840x2160. If the task needs full-desktop proof, use a DPI-aware capture path and validate the saved physical pixel dimensions.

## States To Check

- default view
- compact and wide layouts
- selected/active navigation
- hover/focus when practical
- dialogs, drawers, popovers, menus, and tooltips
- empty, loading, error, and no-results states
- long labels, long titles, sparse data, and dense data
- route or tab changes touched by the redesign

## Functional Walkthrough QA

Before claiming completion, build a small feature matrix for changed and adjacent user-facing functions:

```text
Feature/control:
Action performed:
Expected result:
Actual result:
Pointer/hit area:
Evidence: <screenshot, recording, DOM/state signal, or explanation>
Status: <pass|fixed|blocked|skipped>
```

Exercise relevant:

- navigation, tabs, breadcrumbs, sidebars, and route changes
- buttons, icon buttons, menus, dropdowns, popovers, drawers, dialogs, and tooltips
- search, filter, sort, pagination, selection, bulk actions, and table overflow
- forms, validation, save/cancel, destructive actions, success messages, and error messages
- empty, loading, error, no-results, sparse-data, dense-data, and long-content states
- mobile or compact controls that replace desktop controls

Use mouse or pointer actions where practical. Verify that the visible control can be reached, the clickable hit area matches what the user sees, nearby controls are not accidentally clicked, disabled controls do not appear active, and no overlay blocks a needed action.

After each click, fill, route change, or state transition:

1. Record the expected result before judging the screen.
2. Use the same pointer, keyboard, or touch path a user would use when tools permit.
3. Verify the actual state, route, selection, focus, feedback, and error/runtime status.
4. Capture screenshot, short recording, DOM/state signal, or equivalent evidence after the transition.
5. Inspect the new visual state for text overlap, clipping, overflow, visual pollution, blocked controls, popup/menu/tooltip/drawer placement, hover/focus/active clarity, hit-area mismatch, hidden runtime error, stale selection, route mismatch, unexpected layout shift, and design-intent mismatch.

A no-op, wrong route, hidden runtime error, stale selection, clipped popup, blocked control, hit-area mismatch, or unexpected layout shift is a defect unless there is a clear product reason.

## Visual Defect Checklist

Look for:

- text clipping, overlap, truncation, and awkward line breaks
- controls or badges colliding with neighboring content
- insufficient contrast or muted text that becomes unreadable
- inconsistent spacing, radius, borders, shadows, and alignment
- overly decorative surfaces competing with actual content
- responsive overflow, horizontal scroll surprises, and compressed controls
- missing scroll affordances
- post-click visual pollution, such as menus covering key text, popovers escaping the window, drawers hiding required actions, or tooltips obscuring the thing they explain
- hover, focus, active, selected, disabled, and loading states that do not communicate the current state
- visible controls that cannot be reached by the pointer or whose clickable region does not match the visible target
- UI that looks like a control panel when the target is a calm product surface
- UI that looks like a marketing page when the target is an operational tool

## Visual Style Alignment QA

Before changing functionality, routes, layout architecture, or feature inventory because of a concept mismatch, first check whether the real UI matches the concept's art direction.

Check:

- palette, contrast, saturation, and accent color behavior
- typography scale, weight, density, and rhythm
- surface language: flat, layered, glass, paper, industrial, playful, editorial, or other material treatment
- spacing rhythm, border radius, dividers, elevation, shadows, glow, blur, and depth
- icon, illustration, app icon, and asset style compatibility
- motion and interaction feel when the concept implies movement or state transitions
- whether the visual direction still fits the product type and existing design system

If the style is off but the function is present, fix visual style before making structural or functional changes. Do not chase pixel-perfect placement; preserve the concept's visual language, mood, hierarchy, and material behavior while keeping real workflows intact. After style passes, use `divergence-review.md` to settle functional and structural differences before polishing detailed presentation.

## Presentation, Readability, And Interaction QA

Run this after visual style alignment and after functional/structural divergence decisions have settled which regions, workflows, and routes remain.

Check:

- whether the real UI preserves the concept's intended information hierarchy and scan path for retained areas
- grouping, section order, headings, labels, affordances, and progressive disclosure
- whether content is deliberately composed instead of dumped into available space
- control discoverability, selected/active states, feedback, and error/empty/loading comprehension
- dense, sparse, translated, and long-content cases that can weaken readability without obvious overlap

Fix presentation/readability issues after function and structure are stable. Do not polish a region that should be removed, moved, or replaced by a different workflow.

## Content And Localization QA

When the UI includes real copy or multiple languages, check:

- untranslated strings, placeholder text, or mixed-language leftovers
- incorrect or inconsistent translation of labels, CTAs, empty states, errors, tooltips, and navigation
- date, time, number, currency, percentage, unit, and punctuation formatting
- long English words, CJK text without spaces, and bilingual labels under compact widths
- whether generated concept text was replaced with real implementation copy

## Application Icon And Asset QA

When the product ships as a desktop app, mobile app, packaged web app, or branded software artifact, generate app icon candidates alongside concept candidates, then gate the selected icon before final implementation/package polish.

Core gate: the app icon must be a transparent standalone mark, not a square picture of an icon.

Check:

- app icon style matches the approved UI concept's visual language without copying the UI screen
- the mark is simple, centered, high-contrast, and recognizable as a silhouette
- the icon is not a square tile, rounded-rectangle plate, glass card, framed badge, UI screenshot, mockup, text-heavy mark, or tiny illustration
- any glass, glow, gradient, or depth effect stays inside the mark and does not create a visible background panel
- the icon is not too dense, decorative, gradient-heavy, or dependent on tiny interior detail
- the icon source has a real alpha channel, transparent corners, and no opaque background rectangle; if native transparency is unavailable, generate on a flat chroma-key background and remove it before acceptance
- the icon remains readable at target sizes such as 256, 128, 64, 48, 32, and 16 px; for Windows, verify the sizes that will be embedded in the `.ico` or installer resources
- the icon works on light and dark desktop backgrounds when practical
- the icon has enough padding, no watermark, no accidental text, no trademarked marks, and no unrelated decoration
- Windows desktop, taskbar, title bar, installer, and Alt-Tab contexts do not make the icon read as a small framed picture

When a transparent raster master is available, prefer the bundled helper for mechanical checks and Windows `.ico` export:

```bash
python <autonomous-concept-ui-redesign skill dir>/scripts/app_icon_asset_check.py --input <icon.png> --ico-out <app.ico> --preview-dir <preview-dir> --json
```

Use the script result as evidence for alpha, corner transparency, preview files, and embedded `.ico` sizes. It does not replace visual judgment about whether the mark is too complex or too card-like.

Treat in-UI functional icons separately:

- functional controls reuse the repo's icon library or vector/SVG system where practical
- in-UI icon style matches the UI: stroke/fill, radius, color, shadow, perspective, and visual weight
- in-UI icons remain recognizable at their target sizes such as 16, 20, 24, 32, and 48 px
- icon-only controls have accessible labels and, when useful, tooltips

## Motion, Light, And Depth QA

If the concept implies animation, interaction motion, glow, light, glass, shadow, blur, particles, charts changing, loading shimmer, or depth:

- classify each cue as static styling, microinteraction, state transition, loading/progress animation, ambient animation, data animation, or concept overreach
- define the trigger, duration, easing, affected properties, and reduced-motion fallback for implemented motion
- prefer motion that clarifies state over decorative motion
- verify important motion with a short recording or before/during/after screenshots when a single still cannot prove it
- reject effects that obscure text, reduce contrast, hurt performance, or compete with the workflow

## Iteration Rule

Fix visible defects before moving on. After a fix, capture the affected state again.

If the screenshot shows a difference from the concept, do not automatically chase pixels. Use `divergence-review.md` to decide whether the concept or the implementation should change.

If the screenshot method itself is defective, fix the capture method first. Do not use a partial, wrong-window, or logical-size-only screenshot to pass visual QA.

If functional click-through or real screenshots show that the concept was too vague, too decorative, missing states, or incompatible with real content, revise the concept brief or regenerate the concept before continuing the next visual pass.

## Reporting

Report:

- functional framing and design-language decisions used for QA
- display element review decisions used for QA
- candidate search rounds, scoring summary, and final selection rationale
- concept version(s) used and screenshot round(s)
- screenshots or states inspected
- post-interaction screenshots or equivalent evidence for material clicks/state changes
- concept three-layer and real UI three-layer checks performed in order
- functional walkthrough items checked, fixed, blocked, or skipped, including pointer reachability and expected-vs-actual results
- visible issues fixed
- content/localization, application icon/assets, in-UI icon, and motion/light/depth checks performed
- states not checked and why
- remaining visual risks
