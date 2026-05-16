# FlowPilot Runtime Kit

This runtime kit is copied into each new `.flowpilot/runs/<run-id>/` directory.
It is the only prompt source for formal FlowPilot startup after the bootloader
loads `flowpilot_router.py`.

Rules:

- Cards are data. They do not advance the route by themselves.
- `manifest.json` is the authority for which card may be delivered to which
  role.
- System cards are always `from: system`, `issued_by: router`, and
  `delivered_by: controller`.
- Role-to-role work uses packet/mail ledgers and sealed bodies.
- Formal file-backed PM decisions, reviewer reports, officer reports, and
  GateDecision bodies use `role_output_runtime.py` for skeleton generation,
  mechanical validation, receipts, ledgers, hashes, and controller-visible
  envelopes.
- `flowpilot_runtime.py` is the preferred unified role entrypoint. It delegates
  system-card check-in to `card_runtime.py`, packet/result opens and
  completions to `packet_runtime.py`, and formal reports/decisions to
  `role_output_runtime.py`.
- An ACK-only system card is complete when Router receives the matching ACK.
  That clears the card ACK wait only.
- Any card, mail, or packet that asks for a report, result, decision, packet
  spec, or blocker remains active after ACK. It is complete only when Router
  records the named output event.
- Role-output envelopes should use compact `body_ref` and
  `runtime_receipt_ref` metadata. Legacy top-level path/hash fields are
  compatibility inputs.
- `quality_pack_catalog.json` is route-quality data. The role-output runtime
  validates generic `quality_pack_checks` coverage only; reviewer/officer/PM
  gates own pack-specific quality judgement.
- Controller may deliver cards and envelopes, but must not read sealed packet
  or result bodies, and must not read role-output bodies from envelopes.
