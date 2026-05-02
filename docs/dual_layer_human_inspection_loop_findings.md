# Dual-Layer Human Inspection Loop FlowGuard Findings

Date: 2026-05-01

## Scope

This model tests the proposed FlowPilot architecture repair after route-015
proved that the previous UI route could finish even when the final product was
visibly weaker than the concept target and user acceptance floor.

The modeled architecture preserves the existing FlowPilot route system:

```text
plan -> node -> heartbeat frontier -> route mutation -> verification
```

and adds a recursive inspection system:

```text
evidence -> human-like inspection -> issue grill -> route mutation ->
repair node -> same-inspector recheck -> parent/backward review
```

The key new policy is that every meaningful node has two model scopes:

- a development-process FlowGuard model;
- a product-function FlowGuard model.

This applies to root project scope, parent nodes, leaf nodes, repair nodes, and
final completion review.

## Modeled Route

The model uses a compact route tree that preserves the intended shape:

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

The model includes these representative failure paths:

- visual divergence found by screenshot/concept inspection;
- functional interaction gap found by manual product operation;
- parent rollup conflict found by backward review;
- final rough-product failure found by completion inspection;
- one same-inspector repair recheck that fails once and forces another route
  mutation before the product can complete.

## Architecture Rules Tested

The model verifies these rules:

1. The route tree and heartbeat frontier cannot materialize before the root
   process model and root product-function model pass.
2. A parent node cannot enter child work until parent process and product
   models pass.
3. A leaf cannot write evidence or receive human-like review until both the
   leaf process model and leaf product-function model pass.
4. Human-like review requires context and manual experiments. Screenshot
   existence or app-launch evidence is not enough.
5. Blocking inspection issues must be made specific through inspector grilling.
6. Blocking inspection issues mutate the route and create repair nodes.
7. Repair nodes need their own process and product-function models.
8. Issues close only after same-inspector recheck passes.
9. Parent and final backward reviews are required before completion.
10. Completion is impossible with open issues, missing review state, or missing
    final showcase review.

## Check Results

Commands:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile .flowpilot/task-models/dual-layer-human-inspection-loop/model.py .flowpilot/task-models/dual-layer-human-inspection-loop/run_checks.py
python .flowpilot/task-models/dual-layer-human-inspection-loop/run_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Results:

- FlowGuard schema version: 1.0;
- dual-layer model states: 1128;
- dual-layer model edges: 1162;
- invariant failures: 0;
- missing required labels: 0;
- progress findings: 0;
- stuck states: 0;
- nonterminating components: 0;
- terminal complete states: 31;
- completion paths containing visual divergence repair: 16;
- completion paths containing function-gap repair: 16;
- completion paths containing parent-rollup repair: 16;
- completion paths containing final rough-product repair: 16;
- completion paths containing a failed same-inspector recheck and retry: 15.

Existing FlowPilot models also still passed:

- meta model: 17,944 states and 19,673 edges, no invariant failures, no stuck
  states, no nonterminating components;
- capability model: 3,305 states and 3,469 edges, no invariant failures, no
  stuck states, no nonterminating components.

## Hazard Probes

The runner also injected known bad states to verify that the model catches the
route-015 class of false completion.

Detected hazards:

- frontier written without root product-function model;
- leaf evidence written without a leaf product-function model;
- human-like review marked pass without manual experiments;
- repair evidence written without a repair product-function model;
- completion with an open blocking issue;
- completion without final human-like review.

All hazard probes were rejected by invariants.

## Design Implication

The next FlowPilot skill update should not only say "do better visual QA." It
should make inspection a first-class route mechanism:

- a node produces evidence;
- an inspector reviews evidence with context and experiments;
- a failed review creates a specific issue;
- the issue mutates the route;
- the repair node has its own dual models;
- the same inspector rechecks;
- backward review checks composition;
- final completion requires showcase acceptance.

The model confirms that this architecture can preserve the original
heartbeat/frontier/route-mutation system while preventing the old failure mode
where technical evidence allowed a rough product to complete.

## Residual Blindspots

FlowGuard still does not judge aesthetics directly. The quality of the result
depends on the AI inspector receiving enough context and being required to write
specific, evidence-backed findings. The model verifies the control response to
that finding, not the subjective correctness of the finding itself.

The next production change should therefore update the FlowPilot skill so the
inspector prompts and evidence schema are strong enough to produce useful
blocking issues instead of vague pass/fail text.

