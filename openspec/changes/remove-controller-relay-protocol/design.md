## Context

The current black-box runtime already has the behavior the user wants:
Controller or host code requests a role lease with `flowpilot_new.py
lease-agent`, the assigned role ACKs with `flowpilot_new.py ack`, and the same
lease submits completion with `flowpilot_new.py submit-result`. This path does
not use `controller_relay`.

The blocked run came from the strict packet-runtime surface, where role cards
and `open-packet`/`run-packet` commands still expected a Controller relay
signature. That relay requirement was introduced for an envelope-only
handoff design, but it is not part of the current lease protocol and the
Controller does not naturally emit it.

## Goals / Non-Goals

**Goals:**

- Remove `controller_relay` from the current work-packet protocol.
- Keep assignment/ACK/result mechanics simple and current-run scoped.
- Preserve role identity, body hash, output contract, and sealed-body
  protections.
- Make role cards point at the current runtime path instead of the strict relay
  path.
- Sync source and installed FlowPilot after validation.

**Non-Goals:**

- Do not keep a compatibility layer that accepts or records
  `controller_relay`.
- Do not strengthen the current lease path beyond removing the obsolete relay
  blocker.
- Do not migrate old run artifacts in place; future FlowPilot runs will start
  fresh.

## Decisions

1. Treat lease authority as the current protocol boundary.

   A packet is actionable when the current runtime assigns a packet to a live
   lease, records the ACK, and the matching lease submits the result. Body-open
   helpers may still verify addressed role and hash integrity, but they must
   not require a Controller relay field.

2. Remove relay as a user-facing runtime operation.

   `relay-envelope` exists to create the removed field. The unified runtime
   should not advertise or dispatch it as a current command. Existing
   role-output submission commands stay, because they are used for formal
   report/decision files and do not require Controller relay signatures.

3. Model the failure as a model miss and repair the model.

   The packet-open authority model previously treated "path-only without
   Controller relay" as hazardous. That is now backwards for the current
   protocol. The model should instead block waiting for an extra relay after
   verified current assignment/ACK authority.

## Validation Plan

1. Run FlowGuard project audit before edits.
2. Run targeted packet-open/new-only runtime model checks after edits.
3. Run focused packet runtime and card coverage tests affected by relay
   removal.
4. Validate this OpenSpec change.
5. Rebuild/check FlowGuard project topology if model or source ownership files
   changed.
6. Sync repository-owned skill to the local installed FlowPilot skill.
7. Run local install freshness audit and install check after sync.
