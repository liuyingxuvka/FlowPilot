# Divergence Review

Use this when the implemented UI differs from the concept mockup.

Use the functional framing and display element review as the source of truth for what the UI must help the user understand, do, show, hide, or defer. Use the selected concept set as the source of truth for approved visual direction, hierarchy, and intended presentation quality.

## Review Order

Review divergence in this order:

1. **Visual style alignment first.** Compare palette, typography, surface language, spacing rhythm, icon/asset style, motion, light, shadow, and depth before changing routes, feature inventory, or layout architecture.
2. **Functional and structural fit second.** After the style pass, compare both the concept and implementation against the functional framing and display element review: real workflows, approved visible/conditional elements, data, actions, states, functional zones, navigation, and interaction model.
3. **Presentation, readability, and interaction clarity third.** After function and structure are settled, compare information hierarchy, grouping, scan path, labels, affordances, state clarity, and retained content composition.
4. **Implementation constraints fourth.** Accept or revise differences caused by accessibility, responsiveness, performance, data density, local design-system limits, or technical constraints.

Do not start by reshaping product architecture just because the concept image organizes areas differently. First ask whether the real UI has captured the concept's art direction. If not, fix visual style before functional restructuring unless there is a concrete product reason.

Do not polish detailed presentation before functional structure is stable. Once it is stable, do not pass the UI merely because functions exist and nothing overlaps; retained areas should still be readable, understandable, and intentionally composed.

## Classify Each Difference

### Accept

Accept the implementation when it:

- preserves real functionality better than the concept
- follows the repo's design system more closely
- improves accessibility, responsiveness, or interaction clarity
- avoids fake data or invented controls from the concept
- handles real content length or density better
- preserves the concept's visual language while changing structure for a real product reason
- improves presentation, readability, or interaction clarity for retained functions without changing the product model
- simplifies over-decorative motion, lighting, application-icon, or in-UI icon detail without weakening the workflow

### Fix The UI

Fix the implementation when it:

- misses the concept's visual language, mood, material treatment, typography, color, icon/asset style, or depth cues without a product reason
- loses the concept's primary hierarchy without a product reason
- introduces visible overlap, clipping, crowding, or awkward spacing
- changes the intended surface language into a weaker default look
- hides important actions
- keeps the right functions but presents them as unstructured dumped text, weak grouping, unclear hierarchy, poor scan path, or unclear affordances
- creates inconsistent components, colors, radii, or shadows
- fails at a state or viewport the concept implied should work
- breaks or ignores a real user-facing function during click-through QA
- creates post-click defects such as blocked controls, clipped menus, mispositioned popovers, unreadable state feedback, hit-area mismatch, or visual pollution
- drops a purposeful motion, application-icon, in-UI icon, content, or localization requirement that the concept brief explicitly called out

### Revise The Concept

Revise or discard the concept when it:

- invented features or workflows outside the user's request
- assumed a design system the repo does not have
- used unrealistic density for the product type
- depended on image-only effects that would be fragile or inaccessible in code
- made precise text, charts, or data look better than a generator can truthfully specify
- was too vague to guide layout, state, content, icon, or motion decisions
- was too decorative for the product's workflow or data density
- failed when tested against real content length, translations, or small-screen layouts
- showed a presentation style that cannot support the real app's density, scan path, or interaction states

### Regenerate The Concept

Generate a new concept target only when a revised brief would materially improve the next implementation pass. Regenerate when:

- the first concept cannot be simplified into an actionable target
- real UI screenshots reveal that the concept hid important workflows or states
- the concept's visual language conflicts with the repo's actual design system
- the concept over-relies on glow, glass, particles, 3D depth, or illustration that should not drive the product UI
- the concept's art direction looks strong as an image but fails against the product's real data, density, accessibility, or design-system constraints
- several implementation fixes would only chase a weak or misleading concept

Regenerate or revise the application icon, not necessarily the full UI concept, when the app icon is the only weak asset: a square picture instead of a transparent mark, too tile/card/frame-like, too detailed, too decorative, too close to a screen screenshot, unreadable at small Windows desktop sizes, or mismatched with an otherwise accepted UI concept.

## Decision Summary Template

```text
Concept target/version:
Functional framing used:
Display element decisions used:
Screenshot state:
Key differences:
Visual style alignment:
Functional/structural decisions:
Presentation/readability/interaction findings:
Accepted differences:
UI fixes needed:
Concept revisions needed:
Concept regeneration needed:
Functional walkthrough findings:
Pointer/post-interaction findings:
Content/localization findings:
Application icon/asset findings:
In-UI icon findings:
Motion/light/depth findings:
Next verification screenshot:
```

## Practical Rule

Use the concept to protect direction, hierarchy, visual ambition, and readable presentation. Use the real app to protect functionality, content truth, accessibility, and maintainability.

Run at least one post-implementation divergence review. Continue another loop when material differences remain unresolved. Do not finish with "close enough" if the remaining gap affects workflow, readability, content correctness, interaction, motion, or responsiveness.
