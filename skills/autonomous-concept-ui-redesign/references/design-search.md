# Design Search

Use this after functional framing and design language, before implementation. The goal is to search across several UI concept and app icon directions instead of accepting the first attractive image.

## Search Rules

- Run search for substantial concept-led redesigns. This skill assumes the redesign is large enough to justify it.
- Generate at least three first-round candidate sets before implementation.
- Each candidate set contains a UI concept image.
- If the product ships as a desktop app, mobile app, packaged web app, or branded software artifact, each candidate set also contains a matching app/software icon candidate.
- Candidate sets must test meaningfully different visual language or structure hypotheses. Do not count color tweaks or near-duplicates as separate candidates.
- Do not implement until candidates are scored, second-round candidates are synthesized, and one final set is selected.

## First-Round Candidate Set Template

```text
Candidate name:
Hypothesis: <what this direction tests>
UI concept prompt:
App/software icon prompt if applicable:
Expected strengths:
Known risks:
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
Display element value/load:
Interaction clarity:
Information presentation/readability:
Aesthetic fit:
App icon style match:
App icon small-size readability:
Implementation feasibility:
Risks:
Keepable properties:
Reject or revise:
```

For products without an app icon surface, mark app icon dimensions as not applicable and explain why. For packaged apps, app icon scoring is required.

## Second-Round Synthesis

After scoring first-round candidates:

1. Extract the strongest keepable properties.
2. Remove decorative or fake features that scored well visually but failed functionally.
3. Generate two or three focused second-round candidate sets.
4. Keep UI concept and app icon paired when app icon generation is applicable.
5. Score second-round candidates with the same matrix.

Second-round candidates should be better hypotheses, not random new styles.

## Final Selection

Select one final concept set from all first- and second-round candidates.

The selection rationale must cover:

- why this direction best serves the primary user task
- why its display element choices are valuable and not overloaded
- why its structure and interaction model are clear
- why its information hierarchy is readable
- why its aesthetic language fits the product
- why the app icon matches the UI and remains readable at small sizes, when applicable
- why it is feasible inside the existing repo architecture

If no candidate is good enough, revise the functional framing or search brief and run another bounded search round rather than forcing implementation from a weak concept.

## App Icon Pairing

For app/software icons:

- match the candidate UI's visual language without copying the screen
- use a simple standalone mark, not a square picture
- avoid text, screenshots, framed badges, glass cards, dense symbols, and tiny internal detail
- prefer transparent background or a chroma-key background suitable for removal
- check recognizability at 256, 128, 64, 48, 32, and 16 px before final acceptance when practical
