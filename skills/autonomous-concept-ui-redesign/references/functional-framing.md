# Functional Framing

Use this before choosing aesthetic direction or generating a concept image. The goal is to decide what the UI must help the user understand and do, what deserves to be displayed, and how approved elements should be organized.

## Functional Goal Inputs

- Product job: the main task the UI helps the user finish.
- Primary user: who uses this surface and what they are trying to decide.
- Required content and data: entities, metrics, lists, media, status, timestamps, copy, and context that must remain available.
- Required actions: navigation, creation, editing, selection, filtering, sorting, saving, exporting, destructive actions, and recovery.
- Required states: default, selected, empty, loading, error, no-results, long-content, dense-data, compact, and wide states.
- Required UI events and transitions: which action is available in which state,
  what visible output it creates, and what state comes next.
- Non-goals: features, metrics, AI panels, charts, tabs, or content that must not be invented.

## Display Element Draft

Draft possible visible elements before judging them:

- primary content and key data
- status indicators, progress, health, warnings, and timestamps
- primary actions and destructive/recovery actions
- navigation, tabs, breadcrumbs, search, filters, sorting, and pagination
- feedback, validation, success, error, empty, loading, and no-results messages
- detail panels, previews, metadata, helper text, tooltips, and secondary context
- compact, expanded, hover/focus, selected, and responsive replacement elements

The draft is intentionally broad. It is a candidate inventory, not a commitment to show everything.

## Display Element Review

For each element, decide:

- Why should it be visible?
- Which user task, decision, or action does it support?
- What is lost if it is hidden by default?
- What cognitive load, visual noise, or layout pressure does it add?
- Is it primary information, secondary information, status feedback, action entry, navigation, or hideable detail?
- Which states should show it: default, selected, hover, expanded, empty, loading, error, compact, wide, or admin/debug-only?
- Does it duplicate another element, compete with the main task, or distract from the highest-priority decision?
- If it duplicates another element in the same state or region, is the
  redundancy intentional, such as accessibility, summary plus detail,
  persistent context, or alternate user vocabulary?
- Can it be merged, deferred, moved into progressive disclosure, or removed?

Do not proceed to information architecture until this review identifies what must be visible, what should be conditional, and what should be hidden or removed.

## Information Architecture Inputs

After display element review, define:

- Functional zones: primary work area, navigation, filters, detail panels, status/feedback, command areas, and secondary reference content.
- Zone priority: what gets first attention, what supports it, and what can be lower emphasis.
- Interaction intent: what should be clickable, inspectable, editable, previewable, dismissible, reversible, or persistent.
- Presentation mode: table, card grid, split panel, inspector, timeline, canvas, map, chart, form, dashboard, command palette, or hybrid.
- Content pressure: density, label length, bilingual text, translations, locale formats, and responsive constraints.
- QA implications: states, controls, pointer reachability, hit-area risks, post-interaction visual states, and long-content cases that must be screenshot or clicked later.

## FlowGuard UI Structure Inputs

For any substantial redesign, prepare enough information for the
`flowguard-ui-flow-structure` gate before writing the concept brief:

- Initial UI state.
- UI states, including default, empty, loading, error, success, selected,
  expanded, modal/drawer/popover, compact, and wide variants when relevant.
- Controls, grouped by intended level: global/persistent, contextual region,
  and local item-level controls.
- Events and transitions as `UI event x UI state -> Set(UI output x UI state)`.
- Displayed information, grouped by semantic meaning rather than only by
  visual widget name.
- Parent/child dependencies: which states, controls, displays, panels, menus,
  and overlays depend on which higher-level workflow.
- Candidate stable regions: toolbar, navigation, command strip, primary work
  area, inspector/detail area, feedback/status region, and overlays.
- Duplicate or overlapping information and controls, including the proposed
  redundancy rationale or the reason they should be merged, moved, deferred, or
  removed.
- Model boundaries: states, adjacent workflows, or external systems that are
  intentionally out of scope for this redesign.

Do not convert this into visual style yet. This inventory exists so FlowGuard
can derive hierarchy, placement stability, ownership, and redundancy decisions
before image generation or frontend implementation.

## Framing Template

```text
Primary user/job:
Main decision or task:
Required content/data:
Required actions:
Required states:
Required UI events/transitions:
Non-goals / fake-feature exclusions:

Display element draft:
Element review decisions:
Always visible:
Conditional or progressive disclosure:
Hidden/removed:
Duplicate/redundant information decisions:
Known load or distraction risks:

Functional zones and priority:
Interaction model:
FlowGuard model inputs:
FlowGuard skip reason if not triggered:
Presentation mode:
Content pressure and localization:
Existing system constraints:
Concept implications:
QA implications:
```

## Decisions To Make Before Design Language

- Which information must be immediately visible, and which can be progressive disclosure?
- Which controls must stay near the content they affect?
- Which controls are persistent/global, which are contextual, and which are
  local to one item, state, panel, or overlay?
- Which displayed information has the same semantic meaning, and is that
  duplication useful or just noise?
- Which states need screenshots, click-through QA, pointer reachability checks, or post-interaction visual checks later?
- Is the UI primarily for scanning, comparing, editing, monitoring, exploring, or storytelling?
- Does the content need dense operational layout, calmer task flow, a visual canvas, or a form-first structure?
- What would make the UI functionally wrong even if it looked good?

## Concept Constraints

When writing the concept/search brief, carry forward:

- approved visible and conditional display elements
- model-derived control/display ownership and redundancy decisions when the
  FlowGuard gate ran
- real zones and their priority
- real actions and state changes
- presentation mode and data density
- long-label, multilingual, or responsive risks
- exact non-goals and fake-feature exclusions

If a generated concept violates this framing, revise the brief or regenerate candidates before coding. Do not accept a beautiful concept that changes the product's job, invents false content, or makes real interaction harder to understand.
