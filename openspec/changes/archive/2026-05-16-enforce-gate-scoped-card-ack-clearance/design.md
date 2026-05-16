## Context

FlowPilot already writes committed system-card envelopes, expected runtime read receipts, and direct Router ACK envelope paths into the card/return ledgers. The weak point is the policy boundary around those pending returns: a Controller relay receipt can look like progress, while the Router still needs a clear rule for when pending system-card ACKs must be collected and how to recover when one is missing.

## Goals / Non-Goals

**Goals:**
- Make required system-card ACKs a scoped clearance gate for route/node boundary movement.
- Check the target role's required system-card ACKs again before relaying formal work packets.
- Recover from missing ACKs by reminding the role to ACK the original committed card or bundle.
- Keep ACKs as mechanical read receipts; they must not close target-role work or semantic PM/reviewer/officer gates.
- Add focused executable FlowGuard and runtime evidence without running the heavyweight meta/capability regressions.

**Non-Goals:**
- Do not require screenshots, large proof files, or new human-facing evidence for every ACK.
- Do not change the existing runtime `open-card` / `ack-card` command contract.
- Do not duplicate system cards as the normal response to a missing ACK.
- Do not make Controller delivery receipts count as target-role completion.

## Decisions

1. Use existing pending return ledger records as the durable source of truth.
   - Rationale: the ledger already contains the target role, expected ACK path, receipt path, card/bundle envelope path, and delivery attempt identity.
   - Alternative considered: add a separate global ACK table. Rejected because it would duplicate the return ledger and introduce reconciliation drift.

2. Add scoped clearance metadata to committed card/bundle return records.
   - Rationale: the Router can explain whether it is waiting because of startup, route, node, bundle, or work-packet preflight context without changing ACK submission mechanics.
   - Alternative considered: infer scope only from card IDs. Rejected because current stage/node fields already exist in live delivery context and are more precise.

3. Use reminder-only recovery when the original committed card or bundle artifact is intact.
   - Rationale: a missing ACK means the role has not completed the read-receipt loop, not that the card is lost. The cheapest safe recovery is to point the role back to the original envelope and expected ACK path.
   - Alternative considered: reissue the system card whenever ACK is missing. Rejected because it creates duplicate delivery identities and can make the Router unsure which ACK closes the scope.

4. Keep formal work packet preflight narrow and target-role based.
   - Rationale: before work starts, the Router only needs to know whether that specific target role has cleared required system-card context for the current scope.
   - Alternative considered: scan all historical cards globally before every action. Rejected because it can overblock unrelated roles and route phases.

## Risks / Trade-offs

- Reminder-only recovery can leave a bad/lost original envelope unresolved longer. Mitigation: preserve recovery as an exceptional path when the committed artifact or hash is missing, stale, or the role was replaced.
- Scoped clearance relies on metadata written at card delivery time. Mitigation: existing records remain usable; missing scope falls back to pending return identity instead of treating the ACK as complete.
- Focused checks do not replace full meta/capability regression. Mitigation: this change includes targeted FlowGuard and runtime tests, and records that heavyweight checks were skipped by user request.
