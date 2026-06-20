## Context

FlowPilot already has current-contract packet/result validation, a synthetic
agent coverage matrix, FlowGuard evidence artifacts, PM repair packets, and a
Controller break-glass lane. The live WorldGuard run showed a gap between those
surfaces: the FlowGuard result body could be mechanically valid while the
packet-owned formal artifact was missing or incomplete, and the fake-AI
rehearsal helper had been writing that artifact automatically instead of
testing realistic omission/malformed cases.

The repair must stay current-contract only. It must not accept old field names,
old run paths, wrapper shapes, missing-field defaults, or body-only substitutes
for required formal artifacts.

## Goals / Non-Goals

**Goals:**

- Make fake-AI coverage explicitly exercise formal artifact lifecycle failures:
  missing file, invalid JSON, missing internal fields, wrong decision values,
  wrong path/currentness, and body/artifact decision conflicts.
- Make runtime reissue feedback executable when a formal artifact fails:
  identify the missing artifact, path, required internal field, allowed values,
  and the fact that result body repair alone is insufficient.
- Project FlowGuard formal evidence paths and failed-check summaries into PM
  repair packets using existing current-contract surfaces.
- Count same-family mechanical formal-artifact failures toward the existing
  fifth-attempt break-glass threshold while keeping attempts 1-4 in normal
  repair/reissue.
- Bind the observed WorldGuard failure family into historical replay and
  ordinary tests before claiming coverage.

**Non-Goals:**

- No compatibility aliases, fallback parsing, old-path promotion, or silent
  conversion of body-only submissions into valid formal artifacts.
- No new role, packet family, or parallel candidate ledger.
- No broad redesign of reviewer or FlowGuard authority.
- No claim that synthetic coverage proves live AI semantic quality or target
  project completion.

## Decisions

### Decision: Treat formal artifacts as a Cartesian material axis

Formal artifacts are packet-owned material, not incidental setup. The fake-AI
matrix will include artifact state, artifact path/currentness, artifact
content shape, result-body state, and retry attempt as separate finite axes.
This follows ContractExhaustionMesh: declare the boundary first, then generate
case ids and oracles. It prevents helper-written artifacts from hiding the
body-plus-artifact failure class.

### Decision: Keep artifact repair on the existing same-packet reissue path

When the formal artifact is missing or malformed, runtime still rejects the
current result and issues a same-family reissue packet. The reissue payload
will use existing `evidence_output_policy`, `missing_required_fields`,
`mechanical_contract_failure`, and contract fields, with clearer wording and
artifact-specific projection. It will not add a fallback path that accepts
partial or historical evidence.

### Decision: Project existing FlowGuard evidence context to PM

The stage evidence matrix already requires `flowguard_evidence_path` for
`flowguard_failure` PM repair decisions. Runtime will derive that value from
the existing FlowGuard work order / packet-owned evidence artifact decision
and include concise failed-check details when available. This is a projection
repair, not a new authority surface.

### Decision: Mechanical same-failure loops share the break-glass threshold

Repeated mechanical formal-artifact failures can leave normal repair stuck
without creating active semantic blockers. Runtime will compute a repeat key
from current contract family, packet family, route node, repair blocker, and
missing formal-artifact field/path. Attempts 1-4 remain normal reissues.
Attempt 5 emits the existing break-glass requirement for Controller diagnosis.

### Decision: Test first, then minimal runtime changes

The implementation order is red-green: add fake-AI and ordinary tests that
fail on current behavior, then apply the smallest runtime changes that satisfy
those tests. Background model checks may run in parallel, but their progress
logs are not completion evidence until final exit artifacts exist.

## Risks / Trade-offs

- Artifact cases can expand quickly -> keep the Cartesian axes finite and
  shard them through TestMesh-owned focused tests.
- Reissue feedback can become verbose -> require only executable fields:
  artifact name, exact path, missing field, allowed values, and body-only
  insufficiency note.
- Mechanical retry counting could over-trigger break-glass -> key loops by
  same current packet family/root cause and reset on successful repair or
  changed failure class.
- PM packets may expose too much evidence -> include paths, hashes, failed
  check ids, and summaries only; do not copy sealed bodies into Controller or
  unauthorized surfaces.
