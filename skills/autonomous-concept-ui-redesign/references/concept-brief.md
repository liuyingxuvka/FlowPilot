# Concept Brief

Use this before generating a concept mockup. The goal is to make the generated image serve the real product instead of inventing a different one.

For formal concept-led UI redesign, the concept target must be selected from a mandatory multi-candidate search using raster images generated with `imagegen`, an authoritative user-supplied visual reference folded into the search as a constraint, or an explicit recorded waiver/blocker. Do not create an HTML/CSS page and screenshot it as a substitute concept target. HTML/browser/desktop screenshots are implementation prototypes or rendered QA evidence unless the user supplied that exact visual as the pre-implementation reference.

## Required Inputs

Complete functional framing first. The concept brief should inherit:

- primary user job and main decision/task
- required content, data, actions, and states
- approved display elements: always visible, conditional, hidden/removed, and known load risks
- functional zones, region priority, navigation path, and interaction model
- FlowGuard structure contract when triggered: model-derived hierarchy,
  global/contextual/local control ownership, event ownership, display
  ownership, stable regions, overlays, redundancy decisions, unresolved states,
  and revalidation notes
- presentation mode: table, cards, split panel, inspector, dashboard, timeline, canvas, form, or hybrid
- content pressure: density, long labels, multilingual copy, locale formats, and responsive risks
- non-goals and fake-feature exclusions

Then add design language:

- Product purpose: what job the UI helps the user finish.
- Current UI problem: what feels visually wrong or hard to use.
- Target visual direction: calm technical, dense operational, editorial, playful, industrial, etc.
- Design constraints: existing tokens, components, brand assets, icons, and density needs.
- Visual style anchors: palette, typography, surface language, spacing rhythm, icon/asset style, motion, light, shadow, and depth cues that should survive implementation.
- Color roles: page/background surfaces, foreground text, muted text, dividers,
  accent color, selected/hover/focus colors, success/warning/error colors, and
  disabled treatment.
- Presentation/readability anchors: information hierarchy, grouping, scan path, labels, affordances, state clarity, and long-content risks for retained areas.
- Content and localization constraints: languages, precise copy, date/time/number/currency formats, and translation risks.
- Application icon needs: whether the product needs a Windows desktop/app icon, existing app icon assets, transparency requirements, target package formats, and small-size constraints.
- In-UI icon needs: existing icon system, new functional icons needed, target sizes, and style constraints.
- Motion and light/depth cues: hover, selected, loading, transitions, glow, shadow, glass, or ambient effects that may need implementation.
- Functional QA scope: controls, routes, states, pointer reachability, post-interaction visual states, and adjacent workflows that must be clicked through after implementation.

## Concept Brief Template

```text
Use case: ui-mockup
Asset type: concept mockup for an existing product UI redesign
Product context: <what the app/tool does>
Primary user/job: <who uses this and what they need to accomplish>
Functional framing: <required content/data/actions/states, zones, interaction model, presentation mode>
FlowGuard structure contract: <triggered/skipped; model id; hierarchy; regions; control/display ownership; overlays; duplicate information/control decisions; unresolved states>
Display element decisions: <always visible, conditional, hidden/removed, value/load risks>
Existing functionality that must remain visible: <real workflows, controls, data>
Current UI problem: <why redesign is needed>
Target design language: <aesthetic direction chosen after functional framing>
Visual style anchors: <palette, typography, surfaces/materials, spacing rhythm, icon/asset style, motion/light/depth cues to preserve>
Color contract: <background surfaces, foreground text, muted text, accent, selected, hover/focus, status colors, disabled, contrast risks>
Functional zones and structure: <primary regions and hierarchy>
Presentation/readability anchors: <information hierarchy, grouping, scan path, labels, affordances, state clarity, long-content risks>
Data density: <compact, balanced, spacious; explain why>
Interaction states to imply: <selected, empty, modal, filters, navigation, etc.>
Content/localization: <languages, copy constraints, formatting rules, translation risks>
Application icon direction: <Windows desktop/app icon needed or not; match concept style; transparent standalone mark; no tile/card/frame; simple silhouette; no tiny detail; target sizes/formats>
In-UI icon direction: <reuse existing icon system; new functional icons; size and style constraints>
Motion/light/depth cues: <static styling only, microinteractions, loading motion, glow/shadow/glass cues>
Functional QA targets: <controls, routes, states, pointer reachability, post-interaction screenshots, and adjacent workflows to exercise later>
Must avoid: invented features, fake analytics, marketing hero layout, unreadable tiny text, decorative clutter, over-detailed icons, animation that obscures function
Text policy: use short placeholder labels only; precise copy will be implemented in code
Output: polished high-fidelity raster concept candidate from imagegen, not a marketing poster or HTML screenshot
```

## Prompt Rules

- Bind every major visual region to a real product function from the functional framing.
- Bind every major visual region to the FlowGuard structure contract when the
  gate ran. Do not let an attractive concept move persistent/global controls
  into local panels, hide required recovery controls, duplicate same-level
  actions, or split one semantic display across regions without a recorded
  redundancy rationale.
- Generate candidates through `design-search.md`: at least three distinct first-round concept sets, diagnosis, scoring, second-round synthesis, concept refinement, readiness check, and final selection before coding.
- Ask each candidate for one coherent screen, not a collage of variants.
- Prefer layout, hierarchy, and surface quality over detailed fake copy.
- Do not include features just because they look impressive.
- If the app is an internal or operational tool, keep it scannable and work-focused.
- If the current repo has a strong design system, ask the concept to respect that direction.
- Capture visual style anchors separately from functional structure so later QA can align the art direction before changing product architecture.
- Capture presentation/readability anchors separately from function inventory so later QA can compare retained areas after functional structure is settled.
- For application icons, pair icon candidates with UI concept candidates when the product ships as a desktop/mobile/packaged app or branded software artifact.
- Ask application icons to match the candidate concept's visual language, but to be a transparent standalone mark: one strong shape, low detail, generous padding, high contrast, no square tile, no glass card, no framed badge, no UI screenshot, no watermark, and no text unless explicitly required.
- If the image tool cannot directly produce transparent output, request a flat chroma-key background suitable for local background removal rather than accepting an opaque square image.
- For in-UI icons, ask for style direction and simple silhouettes, not final tiny production assets unless the user explicitly wants generated raster icons.
- Keep functional in-UI icons in the repo's existing icon library or vector/SVG system when practical.
- For motion and light/depth, ask the concept to imply cues only where they support interaction or hierarchy.

## Selected Concept Three-Layer Review And Refinement Gate

After candidate search and before coding, review the selected concept set in this order:

1. **Visual/art style:** Does it establish usable background surfaces, foreground text, accent/status colors, palette, typography, surface language, spacing rhythm, icon/asset style, and motion/light/depth direction that fits the product?
2. **Functional zones and structure:** Does it preserve the real workflows, required data, actions, states, navigation, and layout zones from functional framing?
3. **Presentation/readability/interaction comprehension:** Does it organize retained content into a clear hierarchy, grouping, scan path, labels, affordances, and understandable state model?

Ask:

- Did the image invent workflows, charts, AI features, tabs, or metrics that are not in scope?
- Did it hide a required action or data region?
- Does it contradict the FlowGuard structure contract's parent/child topology,
  stable placement, control/display ownership, overlay hierarchy, or redundancy
  decisions?
- Did it make density too low for a workflow-heavy app?
- Did it turn a tool into a landing page?
- Does it contradict known technical constraints?
- Can the concept be implemented by extending the existing system rather than replacing it?
- Is the concept too vague to guide layout, state, icon, motion, or content decisions?
- Is it too decorative for the product's real workflow?
- Does it imply dynamic behavior, lighting, or depth that needs an implementation decision?
- Does it create translation, long-label, application-icon, or small-size in-UI icon risks that need later QA?
- Are background colors, foreground text colors, muted text, dividers, accents,
  selected/hover/focus states, and warning/error/success colors clear enough to
  guide implementation?
- Do glow, blur, shadow, transparency, gradients, or dark/light surfaces reduce
  text contrast or make controls ambiguous?

Then decide what happens to the concept before coding:

```text
Final concept version:
FlowGuard structure contract used:
Keep exactly:
Keep as direction, not literal layout:
Remove as fake, duplicate, decorative, or overloaded:
Add back because required by functional framing:
Simplify for implementation, accessibility, density, or responsiveness:
Defer to progressive disclosure:
Color/effect contract to reuse during UI screenshot comparison:
Regenerate image needed: yes | no
Ready for implementation: yes | no
```

Revise or simplify the concept before coding when the answer exposes overreach.
Do not pass a concept merely because its overall art direction is good. A
selected concept that invents scope, hides required controls, overloads the
screen, misses important states, or cannot survive real content should become a
new refined concept version or be discarded before implementation starts.

The selected concept review must produce a reusable final concept evaluation
package. Later UI iteration and deviation review should compare real
screenshots against this package, not only against the bitmap. Keep the package
specific enough to reuse: function coverage, removed extras, hierarchy,
density, color/background/foreground roles, accent and status color behavior,
typography, spacing, surface language, interaction states, and accepted
simplifications.

After the first real UI screenshot, revisit the brief when the implementation reveals that the concept was unclear, over-fancy, hostile to real data, missing states, or too hard to reconcile with the repo's design system. Regenerate the concept only when a revised brief would materially improve the next implementation pass.

For products that need a software/application icon, do not wait until the end of the redesign to discover that the icon does not fit. Generate app icon candidates alongside concept candidates, review the selected icon at small sizes, and revise it before implementing or packaging final app assets.
