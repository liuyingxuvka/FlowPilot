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
- Controller may deliver cards and envelopes, but must not read sealed packet
  or result bodies.
