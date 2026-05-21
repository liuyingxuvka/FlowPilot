# Design Search

Use this after functional framing, the conditional FlowGuard UI Structure Gate,
and design language, before implementation. The goal is to search across
several UI concept and app icon directions instead of accepting the first
attractive image.

## Search Rules

- Run search for substantial concept-led redesigns. This skill assumes the redesign is large enough to justify it.
- Generate at least three first-round candidate sets before implementation.
- Each candidate set contains a UI concept image.
- If the product ships as a desktop app, mobile app, packaged web app, or branded software artifact, each candidate set also contains a matching app/software icon candidate.
- Candidate sets must test meaningfully different visual language or structure hypotheses. Do not count color tweaks or near-duplicates as separate candidates.
- Do not implement until candidates are diagnosed, scored, refined or rejected, second-round candidates are synthesized, and one final concept set passes readiness.
- Treat every generated image as a hypothesis. It may be visually strong and still need functional pruning, state repair, density adjustment, or regeneration before it is fit for implementation.

## First-Round Candidate Set Template

```text
Candidate name:
Hypothesis: <what this direction tests>
UI concept prompt:
App/software icon prompt if applicable:
Expected strengths:
Known risks:
Must preserve:
Must remove or avoid:
```

Useful axes for distinct candidates:

- dense operational vs calmer task-focused
- table-first vs card/panel-first vs split inspector
- restrained flat design vs layered material vs luminous/depth-based surface
- command-heavy workflow vs progressive disclosure
- compact data surface vs visual overview with drill-down

## Scoring Matrix

Score each candidate set from 1 to 5 and write one sentence of evidence for each dimension:

```text
Candidate:
Functional layout:
Required workflow/state coverage:
FlowGuard structure fit:
Display element value/load:
Excess or invented elements:
Interaction clarity:
Information presentation/readability:
Color/background/foreground clarity:
Aesthetic fit:
App icon style match:
App icon small-size readability:
Implementation feasibility:
Risks:
Keepable properties:
Reject or revise:
```

For products without an app icon surface, mark app icon dimensions as not applicable and explain why. For packaged apps, app icon scoring is required.

## Concept Diagnosis And Refinement

After first-round generation, and again before final selection, diagnose the
actual concept images against the functional framing and the FlowGuard
structure contract when the gate ran. Do this even when a candidate looks
visually attractive.

For each candidate, record:

```text
Candidate/version:
Functional completeness: <required workflows, data, actions, and states present or missing>
FlowGuard structure fit: <parent/child topology, global/contextual/local controls, display ownership, overlays, redundancy decisions respected or violated>
Feature load: <extra panels, fake metrics, invented workflows, duplicate controls, decorative clutter>
Display element decisions: <always visible, conditional, hidden/removed respected or violated>
Interaction/state clarity: <navigation, selection, filters, empty/error/loading/long-content states>
Information density/readability: <too sparse, too dense, scan path, grouping, label risk>
Color/effect clarity: <background surfaces, foreground text, accent color, status colors, contrast, glow/shadow/blur risk>
Implementation fit: <repo design system, component availability, responsive/localization risk>
Visual value to keep:
Functional changes before coding:
Visual simplifications before coding:
Color or effect changes before coding:
Decision: keep | refine | discard | regenerate
```

Refine a concept when the visual language is promising but the image has
fixable product issues, such as a missing required action, an overloaded side
panel, decorative charts, vague state model, unrealistic density, or generated
copy that makes fake precision look real.

Discard or regenerate a concept when its product model is wrong, it depends on
fake features, it cannot support the required workflow density, or it would
push implementation toward fragile image-only effects.

When refining, write a revised concept brief that explicitly says what to keep,
remove, simplify, add back, or defer. A refined version can be another raster
concept image or, when the change is small and unambiguous, a written concept
delta attached to the selected image. Large functional or structural repairs
need a new image before coding.

## Second-Round Synthesis

After scoring first-round candidates:

1. Extract the strongest keepable properties.
2. Remove decorative or fake features that scored well visually but failed functionally.
3. Generate two or three focused second-round candidate sets.
4. Keep UI concept and app icon paired when app icon generation is applicable.
5. Diagnose and score second-round candidates with the same matrix.
6. If every second-round candidate still has material functional gaps or overload, revise the search brief and run one bounded refinement round instead of forcing a weak final concept.

Second-round candidates should be better hypotheses, not random new styles.

## Final Selection

Select one final concept set from all first- and second-round candidates.

The selection rationale must cover:

- why this direction best serves the primary user task
- why its display element choices are valuable and not overloaded
- why its structure and interaction model are clear
- why it respects the FlowGuard structure contract when the gate ran
- why its information hierarchy is readable
- why its aesthetic language fits the product
- why the app icon matches the UI and remains readable at small sizes, when applicable
- why it is feasible inside the existing repo architecture

Before implementation, the selected set must pass a readiness check:

- required workflows, data, actions, and states are accounted for
- model-derived hierarchy, stable regions, control/display ownership, overlay
  boundaries, and redundancy decisions are respected when the FlowGuard gate
  ran
- approved visible, conditional, hidden, and removed display elements are respected
- extra generated features, charts, metrics, tabs, or decorative regions are removed or explicitly rejected
- density and hierarchy fit the product's real use, not just the concept image
- color roles are explicit: page/background surfaces, primary foreground text,
  muted text, dividers, accents, selected state, hover/focus, success, warning,
  error, and disabled treatment
- background and foreground colors are readable in the expected light/dark or
  themed context, and decorative effects do not reduce text clarity
- interaction states are concrete enough to guide implementation
- localization, long-content, responsive, and accessibility-visible risks are named
- implementation constraints and accepted simplifications are recorded

After the readiness check, produce a final concept evaluation package. This is
the artifact that implementation and screenshot iteration must reuse:

```text
Final concept version:
FlowGuard structure contract used:
Functions and workflows to preserve:
Elements removed as extra, fake, duplicate, or decorative:
Information hierarchy and layout zones:
Density and readability decisions:
Color roles and background/foreground contract:
Accent/status color usage:
Typography, spacing, surface, shadow, blur, glow, and depth cues:
Interaction states and responsive risks:
Accepted implementation simplifications:
Screenshot comparison priorities:
```

If no candidate is good enough, revise the functional framing or search brief
and run another bounded search/refinement round rather than forcing
implementation from a weak concept. If one candidate is visually strong but not
ready, select it only as a draft direction and create a refined accepted
concept version before coding.

## App Icon Pairing

For app/software icons:

- match the candidate UI's visual language without copying the screen
- use a simple standalone mark, not a square picture
- avoid text, screenshots, framed badges, glass cards, dense symbols, and tiny internal detail
- prefer transparent background or a chroma-key background suitable for removal
- check recognizability at 256, 128, 64, 48, 32, and 16 px before final acceptance when practical
