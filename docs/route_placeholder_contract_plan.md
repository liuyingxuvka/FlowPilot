# Route Placeholder Contract Plan

## Scope

This is a minimal repair for FlowPilot route display semantics. The startup
Mermaid diagram may remain visible as a useful placeholder, but route display
artifacts and UI readers must be able to distinguish that placeholder from a
canonical route map and replace it automatically when real route data appears.

Out of scope:

- changing visible UI copy;
- removing the startup Mermaid placeholder;
- redesigning the route map;
- changing route execution or node completion semantics;
- publishing to remote GitHub.

## Optimization Sequence

| Step | Optimization point | Concrete change | Acceptance signal |
| --- | --- | --- | --- |
| 1 | Placeholder identity | Add explicit placeholder metadata to route display packets when no canonical route source is available. | Startup `user-flow-diagram-display.json` says the diagram is a startup placeholder. |
| 2 | Canonical identity | Add explicit canonical metadata when the display is backed by real `flow.json` or `route_state_snapshot`. | Real route display packets say the diagram is canonical and not a placeholder. |
| 3 | Replacement rule | Add a machine-readable rule saying startup placeholders are replaced when a canonical route becomes available. | UI/readers do not need to infer replacement from `route_source_kind` and node counts alone. |
| 4 | Runtime preservation | Keep the existing startup visual behavior and existing canonical route display behavior. | Startup still shows the placeholder; activated route still shows the Mermaid route map. |
| 5 | Local sync | Sync the repaired skill into the local installed copy and verify install freshness. | Local install audit passes; no remote push is performed. |

## Bug/Risk Checklist

| Risk id | Possible bug from this change | FlowGuard/model expectation | Runtime/test expectation |
| --- | --- | --- | --- |
| R1 | Startup placeholder is treated as a real route map. | Model rejects placeholder diagrams that are marked canonical or omit placeholder identity. | Startup display packet has `is_placeholder: true` and `display_role: startup_placeholder`. |
| R2 | Real route appears but UI keeps the placeholder. | Model requires canonical route display to replace startup placeholder when route source exists. | Activated route display packet has `is_placeholder: false` and `display_role: canonical_route`. |
| R3 | UI must guess replacement from indirect fields like `route_source_kind: none`. | Model requires an explicit replacement rule for placeholders. | Display packet includes `replacement_rule: replace_when_canonical_route_available`. |
| R4 | Canonical route is incorrectly labeled as a placeholder. | Model rejects canonical displays whose placeholder flag remains true. | Route activation test checks canonical packet metadata. |
| R5 | Placeholder metadata leaks source/evidence clutter into user-visible text. | Existing display leak invariant remains green. | Markdown remains title plus Mermaid only. |
| R6 | Draft routes become visible while adding replacement logic. | Existing draft/canonical-source invariants remain green. | Route-display model and router runtime tests still pass. |

## Minimum Done Criteria

- FlowGuard route-display model has hazards for missing or wrong placeholder
  semantics.
- Hazard checks prove the model catches every listed risk above that belongs in
  the model boundary.
- The safe route-display model still passes after the intended repair.
- Unit tests cover startup placeholder metadata and canonical replacement
  metadata.
- Local install sync and local install audit pass.
