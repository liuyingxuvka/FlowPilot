# Dual-Layer FlowGuard and Human-Like Inspection Architecture

Date: 2026-05-01

## Purpose

This document defines the next FlowPilot architecture repair after the route-015
desktop Cockpit run exposed a false-completion failure: the route finished even
though the final product screenshot clearly did not match the concept target or
the showcase-grade acceptance floor.

The goal is not to add a few more hard-coded UI checks. The goal is to unify the
existing FlowPilot control system:

```text
plan -> node -> heartbeat -> route mutation -> verification
```

with a recursive inspection system that behaves more like a human reviewer:

```text
evidence -> inspect -> explain defects -> mutate route -> repair -> re-inspect
```

FlowGuard remains the executable model for control flow and state transitions.
The AI reviewer remains responsible for qualitative judgment, visual judgment,
manual interaction experiments, and product-specific critique. FlowGuard then
enforces what must happen when that reviewer finds a defect.

## Core Rule

Every meaningful node has two FlowGuard scopes:

1. **Development-process model**: how FlowPilot should complete this node.
   This model covers route entry, current-node ownership, heartbeat recovery,
   child-skill use, evidence creation, validation, inspection, repair, and
   parent rollup.
2. **Product-function model**: how the product or feature itself should behave.
   This model covers user actions, product state, UI transitions, data loading,
   failure modes, runtime interactions, and feature-specific acceptance.

This applies at every level:

- root project;
- phase;
- function group;
- leaf node;
- repair node;
- completion review.

The product model is not optional because a process can be valid while the
product is still bad. Route-015 proved that checking "a screenshot exists" and
"the app opens" does not prove that the product is good.

## Execution Shape

FlowPilot still uses the existing route tree and heartbeat frontier. The change
is that route nodes cannot be considered done until their model pair and
inspection obligations close.

```text
start full-auto
  -> freeze showcase acceptance floor
  -> run layered self-interrogation
  -> build root process model
  -> build root product model
  -> generate candidate route tree
  -> check route tree
  -> write heartbeat frontier
  -> enter the smallest current node
```

For each parent node:

```text
enter parent
  -> load current child subtree
  -> rerun parent process model
  -> rerun parent product model
  -> adjust subtree through route mutation if needed
  -> enter child nodes
  -> run backward parent inspection after children finish
  -> close parent only when product and process rollups pass
```

The parent closure step is mandatory for every non-leaf level. Local child
passes do not automatically imply parent success. After the children pass,
FlowPilot must replay their evidence against the parent product-function model
and perform a human-like backward review of the parent goal. If that review
fails, the route changes structurally: it can jump back to an affected existing
child, insert an adjacent sibling child, rebuild the child subtree, or bubble
the impact to a higher parent. The parent can close only after the changed
child/subtree passes and the same parent backward review runs again.

For each leaf node:

```text
enter leaf
  -> run leaf process model
  -> run leaf product-function model
  -> derive local tests and manual experiments
  -> implement the leaf
  -> write evidence
  -> run local validation
  -> run human-like inspection
  -> close leaf only when the inspector passes it
```

If any inspector fails the node:

```text
inspection failure
  -> grill the inspector result for specificity
  -> record blocking issue with evidence
  -> mutate the route by adding a repair node
  -> invalidate affected rollups/evidence
  -> run repair process model
  -> run repair product model
  -> implement repair
  -> re-inspect with the same inspector class
  -> close issue only after recheck passes
  -> resume original node or parent rollup
```

## Human-Like Inspectors

The inspector is not a passive checklist. It should simulate a real evaluator
with context and experiments.

Required inspector classes:

- **Requirement inspector**: checks whether the user intent and acceptance floor
  were preserved.
- **Architecture inspector**: checks source-of-truth, state ownership,
  route/frontier behavior, recovery, and mutation rules.
- **Product-function inspector**: checks the product behavior against the
  product-function model, not just against implementation existence.
- **Interaction inspector**: operates the product with real user actions,
  including hover, click, tabs, settings, tray lifecycle, language switching,
  sponsor entry, and failure paths when relevant.
- **Visual inspector**: compares concept target, implementation screenshot,
  density, hierarchy, readability, motion, visual clarity, and product polish.
- **Localization/content inspector**: checks that language changes affect the
  whole UI and that visible text is coherent and not duplicated.
- **Conflict inspector**: looks for duplicate controls, overlapping roles,
  hidden assumptions, stale data, and mismatched UI/state semantics.
- **Completion inspector**: asks whether the result is a complete product, not
  merely a running artifact.

Each inspector can produce:

- pass;
- non-blocking note;
- blocking issue;
- request for more evidence;
- request to rerun or expand a product model;
- request to mutate the route.

For UI, browser, desktop, rendered-output, and interaction gates, inspector
work cannot be delegated to a worker report. Automated screenshots and
interaction logs are pointers. The inspector must personally walk the surface or
block the gate with a concrete reason it cannot be operated. The report records
the opened surfaces, window sizes, click or keyboard paths, reachable and
unreachable controls, text overlap or clipping, whitespace/density/crowding,
hierarchy/readability, responsive fit, aesthetic verdict when visual quality is
in scope, and repair suggestions for PM routing.

## Inspector Grill

When an inspector finds a blocking issue, the issue is not accepted as a vague
complaint. The inspector result must be grilled until it becomes repairable.

The issue record must include:

- observed evidence;
- expected behavior or appearance;
- actual behavior or appearance;
- severity;
- affected node;
- affected parent rollups;
- affected product model;
- likely cause or uncertainty;
- repair node target;
- recheck condition;
- same-inspector recheck requirement.

This is where qualitative review becomes stateful process data. FlowGuard does
not decide whether the UI is beautiful; it enforces that a failed visual review
cannot be ignored, cannot be closed vaguely, and cannot allow completion until a
repair and recheck close it.

## Immediate Checks vs Backward Checks

FlowPilot needs both.

Immediate node checks happen right after a node produces evidence:

```text
leaf evidence -> validation -> inspector -> repair or close
```

Backward checks happen after a group, phase, or full product finishes:

```text
latest output -> parent goal -> sibling consistency -> root acceptance floor
```

Backward checks are necessary because some failures only appear after
composition. A UI element may pass locally but conflict with the overall
layout. A language toggle may work in a settings panel but fail across the full
product. A concept may be respected in one section but lost in the final
screen.

Backward review can jump back to:

- the current leaf;
- a sibling leaf;
- a parent group;
- the original concept node;
- the product architecture node;
- the root acceptance contract;
- a new repair node inserted beside the failed scope.

The route tree must change through the formal route-mutation loop when this
happens.

When the backward issue is structural, the mutation target must be explicit:

- **existing child rework**: invalidate the affected child evidence and parent
  rollup, then rerun that child;
- **adjacent sibling insertion**: add the missing sibling node and run it
  through the same model, evidence, validation, and inspection gates;
- **subtree rebuild**: discard stale child-subtree assumptions, rerun the parent
  model, rebuild affected children, and replay the parent review;
- **impact bubbling**: rerun the direct parent first, then higher parents only
  when the changed contract or interface affects them.

## Route Mutation on Inspection Failure

Inspection failure is a first-class route mutation trigger.

Examples:

- visual inspector finds screenshot/concept divergence;
- product-function inspector finds missing interaction semantics;
- conflict inspector finds duplicated controls;
- localization inspector finds partial bilingual coverage;
- completion inspector finds a rough demo instead of a complete product.

Mutation behavior:

1. Enter mutation boundary.
2. Quiesce current node.
3. Preserve the old route version.
4. Record issue evidence and inspector identity.
5. Add repair node or replace/split/reparent affected node.
6. Invalidate stale evidence.
7. Reset affected parent rollups.
8. Recheck the mutated route.
9. Write the next frontier.
10. Resume at the repair node or affected original node.

The heartbeat setting should not be repeatedly rewritten for normal next-step
changes. The heartbeat reads a stable frontier file. The frontier says:

- current node;
- node completion state;
- next node;
- pending repair nodes;
- pending parent rollups;
- route version;
- whether the active node is safe to resume after interruption.

## Product-Function Modeling

The product-function model is built at the same scope as the process model.

At root scope, it models the product as a whole:

- main user jobs;
- visible product states;
- live data sources;
- shell/window/tray behavior;
- multi-task behavior;
- settings/language behavior;
- sponsor/donation behavior;
- concept and visual language commitments;
- failure and recovery behavior.

At function-group scope, it models the group:

- inputs;
- product state read and written;
- user operations;
- visible output;
- edge cases;
- interactions with sibling groups.

At leaf scope, it models the smallest behavior:

- one feature or UI behavior;
- user action sequence;
- expected state transition;
- expected visual/content result;
- local failure modes;
- evidence needed for inspection.

At repair scope, it models the defect:

- what failed;
- why the previous model did not catch it;
- what changed in product behavior;
- what evidence proves the repair;
- what same-inspector recheck must pass.

## FlowGuard Responsibilities

FlowGuard should model:

- the route tree lifecycle;
- current-node ownership;
- heartbeat frontier recovery;
- parent/child transitions;
- process-model and product-model gates;
- validation gates;
- inspection gates;
- issue-specific repair loops;
- route mutation and evidence invalidation;
- parent rollup and backward inspection;
- completion eligibility.

FlowGuard should not pretend to score aesthetics. It should instead enforce
control-flow invariants such as:

- no implementation without a product-function model;
- no leaf close without human-like inspection;
- no parent close without backward review;
- no route completion while a blocking issue is open;
- no issue closure without inspector grilling and same-inspector recheck;
- no completion from screenshot existence alone;
- no repair without its own process and product models;
- no route mutation without route-version evidence and frontier update.

## Completion Rule

The route can complete only when all of these are true:

- root process model passed;
- root product-function model passed;
- every parent has process and product rollup review;
- every leaf has process model, product model, evidence, validation, and
  human-like inspection;
- every blocking issue is repaired and rechecked by the same inspector class;
- backward review passed from final output to root acceptance;
- final product reviewer agrees the result is showcase-grade;
- heartbeat/manual-resume lifecycle is closed in the correct order.

This is intentionally stricter than "tests pass" or "the app opens." It is
designed to prevent the exact failure where a visually poor or functionally
incomplete product is marked done because the technical pipeline completed.

## Current Modeling Target

The executable FlowGuard model for this architecture should verify a compact
but representative route:

```text
root project
  -> parent group: visual/product language
      -> leaf: concept mapping
      -> leaf: rendered UI behavior
  -> parent group: interaction/runtime behavior
      -> leaf: click/hover/drilldown behavior
      -> leaf: tray/tabs/settings/sponsor behavior
  -> final completion review
```

The model should include representative failure paths:

- a visual divergence found by screenshot inspection;
- a functional interaction gap found by manual operation;
- a parent rollup conflict found by backward review;
- a final rough-product gap found by completion review;
- one failed repair recheck that forces a second repair iteration.

The expected result is not that every path is short. The expected result is
that every path either:

- reaches showcase completion after repair and recheck; or
- blocks visibly with a concrete reason instead of falsely completing.
