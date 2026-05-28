## Context

FlowPilot already refreshes parallel packet batches from durable result
envelopes for `material_scan`, `research`, `current_node`, and `pm_role_work`.
The recent research repair added event folding for `research`, but the
implementation still has family-specific reconciliation paths and confidence
reports that can go green without proving all sibling packet-result families.

The owner boundary remains Router durable wait reconciliation. Controller wait
audits stay observers, and sealed packet/result bodies remain unread by Router.

## Goals / Non-Goals

**Goals:**

- Reuse the existing durable-result refresh and Router event-recording path.
- Make packet-result reconciliation a family obligation across
  `material_scan`, `research`, `current_node`, and `pm_role_work`.
- Add FlowGuard obligation-family parity evidence so missing sibling tests,
  stale proof, wrong provenance, or scoped-only evidence block broad claims.
- Add focused runtime tests for full and partial durable-result reconciliation
  without relying on manual result-return events.
- Keep install sync and install audit serialized after code/test/model changes.

**Non-Goals:**

- Do not add a parallel daemon, poller, or Controller-owned mutation path.
- Do not read or summarize sealed packet/result bodies during reconciliation.
- Do not rewrite the packet runtime, role-output runtime, or route frontier.
- Do not archive or overwrite peer-agent OpenSpec changes.

## Decisions

1. Keep the family registry inside the existing work-packet reconciliation
   boundary.

   The runtime already has `_refresh_all_parallel_packet_batches_from_durable_results`
   and Router-owned event writers. Extending that owner is smaller and safer
   than adding a second reconciliation layer.

2. Preserve specialized validators and writers per family.

   `material_scan`, `research`, `current_node`, and `pm_role_work` share the
   envelope-to-event invariant, but their validation payloads and side effects
   differ. The registry should centralize the family contract while allowing
   family-specific payload builders and writers.

3. Treat `worker_current_node_result_returned` and `role_work_result_returned`
   as batch-progress events, not whole-family terminal flags.

   If one member was manually recorded and another durable envelope already
   exists, reconciliation must still fold the remaining sibling member before
   next-action selection.

4. Add a focused FlowGuard model instead of expanding only prose docs.

   The model will use FlowGuard obligation-family parity and analogous-defect
   scans to prove that the observed research miss derives sibling checks for
   material scan, current-node, and PM role-work.

5. Feed family parity into model-test alignment and known-friction confidence.

   Existing coverage and known-friction reports must not claim full confidence
   for this class when the packet-result family evidence is missing, stale, or
   scoped.

## Risks / Trade-offs

- Broad registry can hide family-specific side effects -> Keep validators and
  writers pluggable and test family-specific payloads.
- Existing tests may depend on manual events -> Add durable-envelope-first
  tests while keeping manual-event compatibility.
- Peer-agent changes are active -> Keep this change in a separate OpenSpec
  directory and review overlapping files before each edit.
- Heavy regressions can run long -> Use documented background artifacts and
  inspect exit/status files before reporting completion.

## Migration Plan

1. Add OpenSpec deltas and focused tasks for packet-result family parity.
2. Add or extend the focused FlowGuard family parity model and checker.
3. Update Router reconciliation to fold remaining durable evidence for every
   packet-result family before waits/reminders are selected.
4. Add focused runtime tests for full, partial, mixed manual/durable, wrong
   recipient, and sealed-body provenance paths.
5. Run focused tests, FlowGuard checks, install sync, install audit, and
   selected tier/background regressions.
6. Leave peer OpenSpec changes unarchived unless explicitly requested.
