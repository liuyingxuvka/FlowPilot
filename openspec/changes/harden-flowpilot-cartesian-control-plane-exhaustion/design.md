## Context

FlowPilot control-plane checks currently cover known packet/result contracts,
historical failures, and targeted synthetic-agent rows. Those checks are useful
but do not make an explicit finite-product claim. A live run can still combine a
known material defect with a different handoff context or downstream consumer
and expose a path that no test consumed end-to-end.

The project rules require current-contract repair only. Mechanical validity is
owned by runtime/router, substantive process state by FlowGuard, and quality by
reviewer. This design preserves that split and adds one model-owned Cartesian
layer that proves every declared combination is either applicable and tested, or
inapplicable with a concrete reason.

## Goals / Non-Goals

**Goals:**

- Declare the finite FlowPilot control-plane boundary inventory.
- Declare the finite mutation alphabet covering missing body, missing field,
  malformed value, stale identity, wrong path, missing evidence, unauthorized
  read, unsupported command, duplicate packet, same-blocker repeat, and
  terminal/lock failures.
- Generate a deterministic Cartesian matrix over boundaries, mutations, handoff
  contexts, and consumers.
- Attach an oracle to every applicable cell: reject, repairable reissue,
  terminal blocker, or GlassBreak threshold alarm.
- Require precise repair feedback for every non-GlassBreak rejection.
- Require normal repair drills to stay off GlassBreak.
- Register every evidence owner with TestMesh, Model-Test Alignment, synthetic
  coverage, layered boundary proof, and topology.

**Non-Goals:**

- No compatibility aliasing, legacy field translation, fallback parsing, or
  prose guessing.
- No new runtime ledger unless an executable check proves the existing
  packet/result/gate surfaces cannot express the repair.
- No broad release claim from the new matrix alone.

## Decisions

### 1. Add a Layer Above Existing Contract Exhaustion

The new model consumes the current contract-exhaustion mesh instead of editing
it into a larger implicit list. The existing mesh remains the detailed
packet/result contract specialist. The Cartesian layer owns the full product
claim and checks that the specialist cells are consumed by a wider control-plane
matrix.

Alternative considered: expand the existing mesh in place. That would mix two
responsibilities and make it harder to tell whether a future miss is a missing
contract field or a missing cross-context combination.

### 2. Record Skipped Cells, Not Just Applicable Cells

The runner records total product size, applicable cells, skipped cells, and skip
reasons. This prevents false confidence from a filtered matrix where impossible
or unsupported combinations silently disappear.

Alternative considered: generate only applicable cases. That is smaller, but it
does not answer the user's core concern: whether all declared possibilities were
actually considered.

### 3. Make GlassBreak a Threshold Probe Only

Normal repair drill cells MUST expect precise reject/reissue/terminal-blocker
feedback. Only explicit repeat-threshold probe contexts may expect GlassBreak.
The test suite fails if an ordinary material defect treats GlassBreak as success.

Alternative considered: allow GlassBreak as a general liveness outlet. That
would prove the system can stop looping, but not that it can recover without
operator escalation.

### 4. Keep Ownership Mapped to Current Runtime Actors

Every applicable cell names the current subject, mechanical owner, required
repair command, downstream consumer, evidence owner, and validation command.
This keeps fixes model-owned without adding fallback channels.

Alternative considered: use a generic "repair failed" outcome. That would not
give the next AI packet enough information to change its next packet.

## Risks / Trade-offs

- [Large matrix] -> Keep dimensions finite and explicit, summarize counts in the
  result artifact, and place full rows behind deterministic generators.
- [False pass from stale results] -> Runner writes a fresh JSON artifact, and
  tests import the generator directly instead of trusting only prior output.
- [Parallel-agent conflicts] -> Add the new Cartesian layer as separate files
  first, then make narrow registry edits.
- [Over-repair] -> Reject unsupported shapes at the model/test layer unless a
  specific runtime bug is proven by a failing regression.

## Migration Plan

1. Add OpenSpec requirements for the new capability.
2. Add the Cartesian FlowGuard model and runner.
3. Add focused tests and registry hooks.
4. Run the new runner and targeted pytest suite.
5. Rebuild/check topology after registering the model and runner.
6. Record FlowGuard adoption evidence and update OpenSpec tasks.

## Open Questions

None. The current-contract/no-fallback rule is explicit, and the new layer is
additive over existing current FlowPilot contracts.
