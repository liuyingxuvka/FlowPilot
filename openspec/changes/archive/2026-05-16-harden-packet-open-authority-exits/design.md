## Context

FlowPilot already has the pieces needed for this recovery path:

- `packet_runtime.py` verifies Controller relay, target role, and packet body hash before exposing sealed body text to the addressed role.
- Packet ledger records `packet-body-opened-by-recipient` and the active holder role.
- PM startup decisions already include `pm_startup_repair_request` and `pm_startup_protocol_dead_end`.
- Router control blockers already have `pm_control_blocker_repair_decision` and a blocker repair policy row.
- Ordinary workers/reviewers/officers already have blocker and PM-suggestion paths for issues that PM or Router must disposition.

The missing part is not a new route. The missing part is an explicit bridge from "runtime open succeeded" to "you are authorized to work or must submit an existing formal exit."

## Goals / Non-Goals

**Goals:**

- Treat a successful `open-packet` runtime session as explicit authority for the addressed role to work that packet.
- Tell PM that a successful open cannot be reinterpreted as missing relay authority.
- Tell ordinary roles that successful open means work now, while true inability to complete must become a formal blocker or PM-suggestion return.
- Make PM use existing PM exits when PM itself cannot proceed.
- Add executable model coverage for the bad states that caused the stop.

**Non-Goals:**

- Do not create a new PM blocker flow.
- Do not change sealed body visibility or allow Controller to inspect packet/result bodies.
- Do not alter the active-writer settlement or monitor current-work ownership changes being handled by parallel work.
- Do not change PM decision authority or ordinary role completion authority.

## Decisions

1. **Runtime success carries an authority object.**

   `begin_role_packet_session` will return and persist `work_authority` metadata. It is controller-safe session metadata only, not body content. It says the session was authorized by the runtime, verified by relay/hash checks, and requires the role to submit either the expected packet result or a formal existing blocker/recovery exit.

2. **Packet ledger records the same authority fact.**

   The packet ledger will record `packet_open_authorizes_work: true` and the required exit family. This lets Router, monitor, and later audits distinguish "opened and working" from "still waiting for relay."

3. **PM has PM-specific recovery exits.**

   PM cannot send a generic blocker to PM and wait. If PM cannot proceed after a verified open, the legal choices are the existing PM repair/stop contracts: startup repair request, startup protocol dead-end, or a control-blocker repair decision when the current input is a Router control blocker.

4. **Ordinary roles use existing blocker disposition.**

   Workers, reviewers, and officers continue work after successful open. If they cannot complete, they must return the existing formal blocker or PM suggestion supported by their packet/card contract. The blocker means "PM/Router must decide or repair this"; it is not a request to silently wait.

5. **No new flow is added.**

   The change strengthens metadata, prompts, and model checks around existing routes. If a later implementation needs richer blocker bodies, that should extend existing contracts instead of adding a separate PM-recovery channel.

## Risks / Trade-offs

- [Risk] A role could overread "authorized" as permission to ignore packet scope. -> Mitigation: authority is explicitly limited to the addressed packet and role boundary.
- [Risk] PM might still choose the wrong recovery exit. -> Mitigation: prompt text names existing output types/events and the model rejects PM self-blocker loops.
- [Risk] Ordinary roles might route every uncertainty as a blocker. -> Mitigation: guidance says successful open means work; blocker is only for true inability to complete.
- [Risk] Parallel work could touch monitor/wait code. -> Mitigation: this change stays in packet runtime metadata and prompt contracts, and only inspects parallel step ownership after completing this boundary.

## Migration Plan

1. Add the OpenSpec change and focused FlowGuard model.
2. Add packet-open authority metadata to packet runtime sessions, packet envelopes, packet ledger rows, and status packets.
3. Strengthen packet identity boundary and role/PM cards to require work-or-formal-exit behavior.
4. Add focused tests for runtime metadata and prompt coverage.
5. Run focused FlowGuard, OpenSpec validation, focused pytest, install sync, and local install audit.
6. Launch heavyweight FlowGuard regressions in the repository background log contract and inspect artifacts before claiming them complete.

## Open Questions

- None for this slice. Active-writer waiting and monitor current-work display are intentionally left to their existing parallel changes unless they are still unowned after this slice finishes.
