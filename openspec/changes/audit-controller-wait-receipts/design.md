## Context

FlowPilot Controller owns foreground orchestration and waits on Router daemon
status plus the Controller action ledger. It must not read sealed bodies or
judge work quality. Runtime already writes several formal receipt surfaces:
card return ledgers, role-output status packets, role-output ledgers, packet
result envelopes, packet ledgers, Router events, and packet-specific
`controller_next_action_notice.json` files.

The current weakness is that a foreground wait can remain quiet even after a
formal return exists, or after only a `controller_aside` claims completion.
Controller needs a small mechanical audit that checks formal receipt surfaces
without expanding Controller authority.

## Goals / Non-Goals

**Goals:**

- Run a formal receipt audit for every nonterminal Controller wait wakeup.
- Detect formal returns that should release or advance a wait.
- Detect formal returns that exist but did not produce the expected Controller
  action or next-action notice.
- Keep `controller_aside` non-authoritative while using it as a reason to check
  formal receipt surfaces.
- Produce machine-readable status classifications and plain-language user
  summaries for meaningful stuck or recovery states.
- Cover behavior with FlowGuard scenarios, focused tests, and installed-skill
  sync.

**Non-Goals:**

- Do not let Controller inspect sealed packet/result/role-output bodies.
- Do not let Controller decide work sufficiency, approve gates, or close route
  nodes.
- Do not replace Router's event reconciliation or scheduler ownership.
- Do not treat `controller_aside` as completion evidence.

## Decisions

1. **Add a reusable wait receipt auditor.**
   - Decision: implement a runtime helper that accepts the run root and current
     wait metadata, then inspects formal metadata files only.
   - Rationale: putting the scan behind a helper keeps standby, patrol, and
     future wait paths consistent.
   - Alternative rejected: prompt-only guidance, because prompt text cannot
     reliably classify stale ledgers or missing next-action notices.

2. **Classify, do not decide content.**
   - Decision: auditor outputs status classes such as `no_formal_return_seen`,
     `formal_return_ready`, `formal_return_seen_but_wait_not_released`,
     `result_envelope_seen_but_no_next_notice`, `aside_claim_without_formal_return`,
     and `formal_return_malformed`.
   - Rationale: these names separate mechanical control-plane health from work
     content quality.
   - Alternative rejected: a single boolean `has_output`, because it hides the
     difference between ordinary waiting and control-plane stuck states.

3. **Wire the audit into foreground wait wakeups.**
   - Decision: include the audit in Controller standby and patrol timer
     snapshots whenever current wait metadata exists and the run is not
     terminal.
   - Rationale: every Controller wakeup during waiting should have the same
     mechanical view of whether formal receipt evidence already arrived.
   - Alternative rejected: only auditing worker packet waits, because PM,
     reviewer, card ACK, repair, and role-output waits can fail in the same
     way.

4. **Keep user reporting budgeted.**
   - Decision: report only meaningful audit outcomes: control-plane stuck,
     malformed formal return, aside-only completion claim when user asked for
     status, user-required action, blockers/recovery, or terminal states.
   - Rationale: this composes with quiet standby reporting and avoids turning
     routine submission asides into chatter.

## Risks / Trade-offs

- **Risk: audit reads too much.** Mitigation: auditor reads only metadata files
  and tests assert no sealed body path is opened or required.
- **Risk: duplicate reconciliation logic.** Mitigation: auditor classifies
  visible facts and points Controller back to Router-owned actions; it does not
  mutate route progress.
- **Risk: false stuck reports during concurrent writes.** Mitigation: include
  timestamps/evidence paths in the audit output and keep stuck classifications
  advisory until Router reconciliation confirms or repairs them.
- **Risk: interaction with ongoing quiet standby work.** Mitigation: keep this
  change separate from the quiet reporting OpenSpec and preserve the quiet
  speak/silence budget.
