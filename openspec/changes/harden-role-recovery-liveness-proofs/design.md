## Context

FlowPilot already has singleton authority and role recovery concepts, but the
live run showed a narrower proof gap: a new role liveness fault can coexist
with an older successful `role_recovery_report.json`. Current readiness code can
accept the old report because it checks `run_id`, `all_six_roles_ready`, and
agent ids, but not the current transaction, affected role set, or host
addressability evidence.

The repair must preserve daemon/Controller ownership, sealed-body boundaries,
and peer-agent work. It must also avoid treating an attempted role replacement
as proof that the replacement remains reachable by the host.

## Goals / Non-Goals

**Goals:**

- Make role recovery readiness current-transaction scoped.
- Require fresh host addressability proof before role slots, active-holder
  leases, resume replay, or PM resume delivery can rely on a role.
- Reject stale report reclaim after blocked or empty `recover_role_agents`
  receipts.
- Improve daemon fatal-error diagnostics and make routine status output compact
  by default.
- Add FlowGuard and ordinary regression evidence for the observed miss and the
  same-class hazards.

**Non-Goals:**

- Do not change the frozen acceptance contract.
- Do not relax sealed packet/result/report body boundaries.
- Do not restart or resume stopped live runs as part of the repair.
- Do not rewrite the broader daemon scheduler or Controller ledger system.
- Do not archive completed OpenSpec changes owned by parallel work.

## Decisions

1. **Bind recovery readiness to the latest transaction.**
   `role_recovery_report.json` remains the readiness artifact, but readiness is
   valid only when the report transaction, crew slot transaction markers, target
   roles, and latest transaction file agree. This keeps the existing artifact
   shape while preventing stale report reuse.

2. **Separate replacement intent from host liveness.**
   A replacement decision or spawn result is lifecycle progress, not host
   addressability proof. The runtime should carry both signals, and only the
   addressability signal can satisfy active role or packet-holder gates.

3. **Keep reclaim paths but make them proof-aware.**
   Existing receipt effects may reclaim already-written reports for idempotent
   retry, but only when the report proves the same current recovery transaction.
   Otherwise Router should re-expose recovery or produce a control blocker.

4. **Use focused tests before broad regression.**
   The first safety net is targeted failing tests for stale report mismatch,
   unknown host liveness, replacement-not-active, and diagnostic output. Broad
   FlowGuard and meta/capability checks then confirm no control-plane regression.

5. **Compact routine status output without removing full diagnostics.**
   The default CLI state output should avoid dumping full ledgers during
   heartbeat/Controller loops. Full state remains available through an explicit
   full-output option or direct file inspection.

## Risks / Trade-offs

- Current tests may have helpers that assume `agent_id` equals liveness →
  update helpers carefully and preserve existing positive recovery tests by
  passing explicit active proof.
- Stricter readiness can expose latent stale state in historical runs →
  historical replay should classify these as recovery-required, not silently
  pass them.
- Compact state output could surprise callers that parsed full ledgers →
  keep direct ledger files unchanged and add full-output escape hatch.
- Daemon diagnostic additions may increase log size during repeated crashes →
  cap structured diagnostic snippets and record artifact paths rather than
  embedding huge ledgers.
