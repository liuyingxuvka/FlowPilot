## Context

The previous Cartesian matrix proved that FlowPilot enumerated declared
boundary/mutation/context/consumer combinations. FlowGuard 0.51 now makes the
coverage contract stricter: generated combination ids, shard ids, and receipt
ids must be visible to downstream routes. Without that, a local matrix can pass
while TestMesh or ModelMesh cannot tell which generated shard was actually
owned.

## Design

The existing Cartesian model remains the source of FlowPilot-specific oracles
and skip reasons. A new native FlowGuard plan is derived from the same finite
axes:

- boundary axis: declared FlowPilot control-plane boundary ids;
- mutation axis: declared mutation kinds;
- context axis: handoff contexts;
- consumer axis: downstream consumers.

The native interaction group generates the full product. FlowPilot-specific
model-owned shards group applicable cells by evidence owner, context, and
expected reaction. The native report consumes both the full-product shard and
the model-owned shards into one coverage receipt.

Bridge rows from contract-exhaustion and historical failures preserve the source
mutation kind exactly. The runner fails if a source mutation is missing from the
Cartesian alphabet or if any bridge row rewrites it into a different known
mutation.

## Trade-Offs

The native full-product shard is intentionally broad, so it is paired with
smaller FlowPilot-owned shards. This keeps FlowGuard's canonical receipt while
preventing one large shard from hiding downstream consumer gaps.

The result artifact summarizes native combination cases instead of dumping all
case bodies. Tests import the model and runner directly when they need exact
counts.
