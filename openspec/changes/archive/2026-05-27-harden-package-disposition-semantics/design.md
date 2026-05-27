## Context

FlowPilot already has one shared PM package-result disposition mechanism for material-scan, research, and current-node packages. The same runtime writer, output contract, control transaction registry entry, and scoped-event identity family are used for all three package kinds.

The live failure came from the scoped event identity treating `body_hash` as part of the PM package disposition dedupe key. That made two different PM bodies for the same batch/generation appear as two distinct events. The runtime envelope validation passed because both outputs were mechanically valid, while the semantic package identity was not protected.

## Goals / Non-Goals

**Goals:**
- Preserve the existing shared package-disposition path and upgrade it for all package kinds.
- Make one batch/generation have one ordinary PM package-result disposition.
- Represent worker-specific differences inside one PM disposition through per-packet outcomes.
- Keep exact replay idempotent while surfacing conflicting bodies as a control-plane conflict.
- Extend models, source audits, and tests so fake AI packages and live replay audits catch this class.
- Sync the local installed FlowPilot skill only after repository validation passes.

**Non-Goals:**
- Do not create a material-scan-only special case.
- Do not invent a second PM decision workflow outside the existing role-output/runtime/event path.
- Do not allow Controller to inspect sealed worker result bodies.
- Do not change frozen task acceptance or release/publish behavior.

## Decisions

1. Use semantic package identity for dedupe.

   PM package disposition event identity uses `event + batch_id + packet_ids + packet_generation_id`. `body_hash` remains in the stored scope as conflict evidence but no longer creates a new ordinary identity. Alternative considered: keep `body_hash` in the key and add a writer-layer duplicate guard. That still lets pre-writer reconciliation short-circuit incorrectly and leaves source audits blind to the real semantic key.

2. Add body-conflict detection before idempotent replay.

   When the event ledger already contains the same semantic dedupe key, the router compares configured conflict fields such as `body_hash`. Same body returns already-recorded. Different body raises a RouterError that points to repair/reissue rather than silently ignoring or recording a second disposition. Alternative considered: make the later body overwrite the earlier one. That would destroy auditability and make PM authority time-dependent.

3. Store per-packet outcomes inside the single PM disposition.

   The PM disposition payload may include `packet_outcomes`; the writer normalizes it against the actual batch membership and stores it in the canonical disposition and batch summary. When absent, the writer derives a compatible all-packet outcome from the aggregate decision for backward compatibility with older fixtures. Alternative considered: require `packet_outcomes` immediately for every fixture. That is cleaner long-term but would force a broad fixture migration unrelated to the bug fix.

4. Keep aggregate advancement tied to outcomes.

   `absorbed` requires all packet outcomes to be accepted and a formal package release. Rework/block/cancel/route-mutation outcomes are recorded but do not release the reviewer formal gate. Alternative considered: allow an aggregate `absorbed` with per-packet rework as a warning. That recreates the ambiguity that caused the live blocker.

5. Extend model checks at the event and package layers.

   The event-idempotency model gains a package conflict scenario, and source audits require package dispositions to exclude `body_hash` from dedupe while declaring it as a conflict field. Runtime tests cover material, research, and current-node package kinds so this is enforced as a class, not an incident-specific fix.

## Risks / Trade-offs

- Older role-output fixtures lack `packet_outcomes` -> The writer derives outcomes from the aggregate decision while PM-facing contracts recommend explicit outcomes.
- Conflict errors can expose a real stuck run sooner -> This is intended; correction must use the existing repair/reissue path to create a new batch/generation.
- The first fix scope does not add arbitrary PM disposition amendment transactions -> That avoids a new parallel workflow and keeps corrections inside existing batch repair semantics.
- Heavy FlowGuard regressions can take time -> They run in the documented background artifact contract and are inspected before completion is claimed.
