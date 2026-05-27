## Context

The latest full diagnostic has already closed missing model, missing code,
missing test, stale evidence, extra code, and internal-only-test gaps. Remaining
findings are explicit StructureMesh deferrals.

The largest safe target is the model-test-code alignment runner. It is a
validation entrypoint that mixes declaration tables, source-contract audit,
surface diagnostics, background evidence classification, known-bad cases, and
CLI/report assembly. Two runtime candidates are also low-conflict because they
are declarative tables with existing external-contract tests:

- `flowpilot_router_facade_export_manifest_controller.py`
- `flowpilot_router_protocol_external_events.py`

Dirty peer-agent files and state-ordering-sensitive runtime files remain out of
scope for this batch.

## Goals / Non-Goals

**Goals:**

- Keep public compatibility facades and commands stable.
- Reduce the model-test alignment runner into smaller, named ownership modules.
- Split only declarative runtime table modules whose parent can remain a simple
  aggregation facade.
- Refresh diagnostics so completed splits and remaining deferrals stay visible.
- Run final validation, sync the local installed FlowPilot skill, and commit
  scoped local changes.

**Non-Goals:**

- Do not refactor dirty peer-agent files.
- Do not split test helper bases or installer internals in this batch.
- Do not split state-ordering-sensitive modules such as card return settlement
  without a dedicated model target.
- Do not push, tag, or publish.

## Decisions

1. Keep runner filenames as public facades.
   Existing tests, docs, and tier commands reference
   `simulations/run_flowpilot_model_test_alignment_checks.py`; it will continue
   exposing `build_alignment_plan_entries`,
   `build_source_contract_alignment_plan`,
   `build_full_model_test_code_diagnostic`, `build_report`, and `main`.

2. Split by evidence responsibility, not by line count alone.
   The alignment runner will delegate to modules for common declarations,
   family plans, source contracts, known-bad cases, full diagnostics, and report
   assembly. This mirrors the FlowGuard evidence path and makes future failures
   easier to locate.

3. Runtime table splits stay data-only.
   Parent modules retain their public constants/functions while child modules
   own declarative shards. No event names, export keys, schema values, CLI
   behavior, or router state writes change.

4. Validation evidence must be final evidence.
   Background launch/progress is not counted as proof. If a background run does
   not produce final artifacts, the equivalent foreground check must be run or
   the evidence must remain explicitly incomplete.

## Risks / Trade-offs

- Import-cycle risk -> Keep dependency direction one-way: common data -> child
  modules -> report facade -> runner facade.
- Hidden behavior drift -> Preserve public names in the facade and run focused
  parity tests plus model-test alignment.
- Diagnostic honesty risk -> Do not simply hide large files from diagnostics;
  update split metadata only when the public entrypoint is actually reduced and
  remaining child debt is explicit.
- Peer-agent conflict risk -> Avoid currently dirty material/protocol/shared-log
  files and stage only scoped changes.
