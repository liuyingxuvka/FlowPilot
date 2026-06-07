## Context

FlowPilot already has many runtime, fake AI, and FlowGuard checks, but the
checks can still drift when a packet body asks for one result shape while a
runtime gate expects another. The recent high-standard contract failure showed
that fake AI rehearsals can mask this drift by emitting fields not declared in
the packet contract.

The current code already has a field-contract model and packet result contract
rows. This change makes that contract mesh authoritative for runtime blocking,
reissue instructions, fake AI parity, negative tests, and model-test alignment.

## Goals / Non-Goals

**Goals:**

- Keep one explicit packet-result path for each current packet family.
- Make packet body instructions, runtime validation, fake AI output, and tests
  prove the same contract.
- Reject old fields, wrappers, aliases, and fallback evidence as current
  completion evidence.
- Make fake AI contract-blind by default: fake success outputs cannot include
  hidden fields that are not declared for that packet family.
- Keep validation evidence fresh after generated model or test result changes.

**Non-Goals:**

- Do not add compatibility migration for old result shapes.
- Do not make fake AI prove live model semantic quality.
- Do not preserve generic fallback paths for convenience.
- Do not replace reviewer or FlowGuard semantic judgment with field checks.

## Decisions

1. Use a packet-result contract table as the runtime source of truth.

   Runtime validators should expose the contract family id, required fields,
   forbidden fields, missing fields, forbidden fields seen, and a minimal valid
   shape. This makes mechanical failures readable to roles and tests without
   accepting alternative shapes.

2. Keep mechanical and semantic ownership separate.

   Runtime/router owns field presence, forbidden fields, packet kind, route
   scope, and reissue metadata. FlowGuard still owns process/state reasoning.
   Reviewer still owns quality and task satisfaction. This avoids turning
   field checks into fake semantic approval.

3. Treat fake AI as a contract-blind role simulation.

   Fake AI success rows can only emit fields declared by the packet contract.
   Negative rows deliberately omit fields, use old fields, or overproduce
   hidden fields and must be rejected. A fake AI row that passes because it
   knows hidden runtime requirements is invalid evidence.

4. Bind model-test alignment to source checks.

   The FieldContract runner should not only explore model states. It must also
   compare contract rows to runtime validators, fake AI terms, and required
   negative tests. Broad e2e green evidence is scoped until these bindings pass.

## Risks / Trade-offs

- Contract table duplication can become stale if code and model diverge.
  Mitigation: source alignment checks compare runtime symbols, fake AI outputs,
  and tests against the model row set.
- Strict fake AI can reveal more short-term failures.
  Mitigation: failures are useful because they identify missing packet wording
  or runtime mismatch before live agents hit them.
- Reissue bodies become more verbose.
  Mitigation: include only mechanical contract metadata needed for the role to
  correct the current packet.
- Existing generated result files may become stale after contract changes.
  Mitigation: rerun FieldContract, FieldMesh, Model-Test Alignment, topology,
  and layered parent checks before final confidence.
