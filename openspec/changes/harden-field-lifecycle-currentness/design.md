## Context

FlowPilot already maintains a FieldLifecycleMesh parent model, a field-contract
model, and model-test alignment result slots. The current gap is that lifecycle
coverage is mostly field inventory, ownership, validator presence, and
legacy-field disposition. It does not yet express packet/result/frontier
transition semantics such as terminal packet states, append-only result history,
pending route mutations, or derived active-packet projections.

Runtime already has the intended single currentness predicate:
`_packet_is_noncurrent_for_routing`. Some paths use it, while other paths still
filter active packets locally. This creates a split authority without adding a
legacy compatibility layer.

## Goals / Non-Goals

**Goals:**
- Extend the existing field lifecycle workflow so behavior-bearing currentness
  fields project into FlowGuard obligations, code contracts, and tests.
- Keep one current-contract path: Runtime/Router owns mechanical field validity;
  Reviewer and FlowGuard operator do not inspect mechanical fields by prose.
- Preserve append-only historical records without allowing historical packets
  or late results to become current authority.
- Reuse the existing runtime currentness predicate for derived active-packet
  projections.

**Non-Goals:**
- No new compatibility parser, alias, wrapper, fallback, or old FlowPilot path.
- No new runtime ledger family when existing packet/result/frontier/blocker
  fields can carry the repair.
- No broad HFF split or unrelated router refactor in this change.

## Decisions

1. **Use existing FieldLifecycleMesh rather than a new model family.**
   - Add transition-oriented lifecycle states to the existing mesh vocabulary.
   - Add concrete field-contract rows for packet/result/frontier/projection
     fields.
   - Rationale: the workflow already exists; the miss came from incomplete use,
     not missing infrastructure.

2. **Make terminal packet disposition absorbing for current authority.**
   - Late results may be appended to `packet.result_ids` as audit evidence.
   - Late results must not rewrite terminal `packet.status` values into active
     or blocking states.
   - Rationale: history remains visible, but current routing remains single
     path and monotonic.

3. **Route all active-packet projections through the single currentness
   predicate.**
   - Compact console and final closure active-packet scans must not duplicate
     filtering rules.
   - Rationale: derived views must not become parallel authorities.

4. **Use focused same-family tests.**
   - Add tests for late results after each noncurrent packet status, stale
     route-node packets, accepted packet duplicates, and compact/final closure
     projection behavior.
   - Rationale: this closes the model miss class without overfitting to one
     observed run.

## Risks / Trade-offs

- [Risk] Adding too many lifecycle fields could make the model noisy.
  → Mitigation: only behavior-bearing fields that affect routing, acceptance,
  pending route mutation, or derived active views become high-level contracts;
  other discovered fields stay leaf inventory.

- [Risk] A late result might still need audit visibility.
  → Mitigation: preserve result creation and `result_ids` append-only history,
  but mark blocked/quarantined results as non-authoritative.

- [Risk] Focused tests could miss broader replay regressions.
  → Mitigation: run field mesh, field contract, model-test alignment, focused
  runtime tests, and relevant install checks after the patch.
