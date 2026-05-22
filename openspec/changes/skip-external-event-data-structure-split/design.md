## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_protocol_external_event_data.py`

Selected action:

- Explicitly skip the split.

Reason:

- The module is an exported declarative table keyed by external-event phase.
- AST inspection shows no top-level functions and no classes.
- Existing contract tests already compare each phase table against the public
  external-event registry and child shards.

Not selected:

- Scheduler receipt packet-fold, scheduled, and standby candidates, because
  those files are currently dirty and may overlap peer-agent work.
- Startup intake materialization, because it owns startup materialization
  writes and needs a separate startup-specific proof pass.

## Diagnostic Boundary

The diagnostic SHALL distinguish a real deferred split from an explicitly
skipped table-only split. A skipped row is not treated as full behavioral proof;
it only means StructureMesh found no useful branch-pruning target in that
surface.

The skip remains auditable through:

- `split_status = skipped_split`
- `structure_split_status = explicitly_skipped`
- `structure_split_skip_reason`
- external contract tests for the event phase table
