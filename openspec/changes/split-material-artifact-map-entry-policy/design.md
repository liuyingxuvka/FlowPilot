## Context

`flowpilot_material_artifact_map.py` already has a strong FlowGuard model and
ordinary tests proving that the map is an index only, does not copy sealed body
text, and preserves PM/reviewer/runtime authority. This change is therefore a
StructureMesh split, not a behavior change.

## Target Structure

- `flowpilot_material_artifact_map.py`
  - public facade and orchestration;
  - map path/read/source-ref/summary APIs;
  - packet-index traversal and refresh write.

- `flowpilot_material_artifact_map_entries.py`
  - safe source references and sealed body references;
  - material-map entry construction;
  - status/count policy;
  - static artifact entry construction.

Dependency direction is one-way: the public facade imports the child entry
module. The child module imports only packet/runtime primitives and must not
import the facade.

## Compatibility Boundary

The following public names remain owned by `flowpilot_material_artifact_map.py`:

- `MATERIAL_ARTIFACT_MAP_FILENAME`
- `MATERIAL_ARTIFACT_MAP_SCHEMA`
- `material_artifact_map_path`
- `material_artifact_map_source_ref`
- `material_artifact_map_summary`
- `read_material_artifact_map`
- `refresh_material_artifact_map`
- `review_source_entry_ids`
- `reviewable_source_paths`

## Validation Boundary

The split is green only if:

- the FlowGuard material-map model still passes;
- focused material-map runtime/boundary tests still pass;
- model-test alignment remains green;
- full coverage diagnostics no longer report
  `flowpilot_material_artifact_map` as a StructureMesh split finding;
- local installed FlowPilot is synced and fresh.
