## Context

The fresh entrypoint already starts correctly: startup UI output is sealed into
the new current-run ledger, the first PM packet is issued, and PM can ACK and
return a result. The defect is after the PM result. The runtime must request an
explicit FlowGuard operator packet, not a direct FlowGuard side command.
Reviewer then records acceptance only through a packet with a current
`packet_id` and ACK.

## Decision: Role Work Is Always Packet Work

Every backend role in the new formal runtime is represented as a packet. The
runtime distinguishes packet purpose with `packet_kind`, not with side-channel
commands.

- `task`: PM or worker performs project work.
- `flowguard_check`: FlowGuard operator checks a subject
  packet/result for the declared modeled target.
- `review`: Reviewer checks the subject result and FlowGuard evidence.

All packet kinds use the same host lifecycle:

1. runtime issues packet;
2. host records a lease for the packet responsibility;
3. agent ACKs the assigned packet;
4. agent submits a result;
5. runtime applies the packet-kind-specific side effect;
6. runtime closes the lease and advances to the next packet.

## Decision: Side Effects Are Packet-Kind Specific

The generic `submit-result` command remains the single completion surface. A
valid result commits different side effects depending on the packet kind:

- PM `task` result issues a `flowguard_check` packet.
- `flowguard_check` result records a FlowGuard work order pass and issues a
  `review` packet.
- `review` result records independent review acceptance, records system-owned
  validation evidence when the evidence passes, and attempts system-owned final
  backward closure.

## Decision: Direct Commands Are No Longer Formal Flow

Direct FlowGuard/review/validation/close commands are not part of the formal
new flow. Formal operation should use only `status`, `lease-agent`, `ack`, and
`submit-result` after startup; validation and closure are runtime outcomes, not
dispatchable role commands.

## Risks

- If closure still treats all packets as needing FlowGuard/review, gate packets
  can recurse forever.
- If direct commands remain in startup guidance, future agents may bypass the
  symmetric lifecycle again.
- If leases are left active after result submission, status projection can
  imply unresolved work even after terminal closure.
