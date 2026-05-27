## Context

The current implementation already enforces the safer shape in many places: PM-issued material, research, current-node, and PM role-work results return to PM for disposition; absorbed PM dispositions write formal gate package metadata; and Router-owned direct dispatch is required before worker relay. The remaining friction is that older cards, event names, model state fields, and helper names still describe a heavier path where Reviewer appears to approve dispatch or receive raw worker results first.

This change keeps the role boundaries intact while removing duplicate approval surfaces. Router owns mechanical dispatch and relay proof. PM owns semantic result disposition and route or node decisions. Reviewer owns independent quality, source, fact, and gate-package review. Controller remains an envelope-only relay.

## Goals / Non-Goals

**Goals:**

- Make the live packet flow understandable as one path across material, research, current-node, and PM role-work packages.
- Preserve the safety effect of PM release while folding it into the absorbed PM package-result disposition when the formal gate package is written.
- Keep Reviewer from becoming a pre-dispatch approver while preserving Reviewer independence at quality gates.
- Replace misleading "reviewer relay" names with recipient-neutral names without breaking existing callers.
- Update FlowGuard models and tests before claiming the simplification is valid.
- Sync the local installed FlowPilot skill and verify source freshness after implementation.

**Non-Goals:**

- Removing PM result disposition, PM route authority, or PM completion authority.
- Removing Reviewer formal gate checks, direct source checks, or independent challenge obligations.
- Allowing Controller to read packet, result, report, or gate package bodies.
- Removing legacy reviewer-dispatch compatibility in the same pass unless validation proves no active code path or archived fixture depends on it.
- Publishing, pushing to a remote, changing dependencies, or touching unrelated peer-agent work.

## Decisions

1. **Fold PM release into absorbed disposition, not out of the process.**

   An absorbed PM package-result disposition is valid Reviewer release evidence only when it records `formal_gate_package_released: true`, `formal_gate_package_path`, `formal_gate_package_hash`, `reviewer_review_scope`, and `raw_worker_result_bodies_included: false`. This keeps a single PM act without letting Reviewer start from a raw Worker result.

2. **Treat reviewer dispatch as legacy compatibility for new PM-authored work packets.**

   New PM-authored worker/officer packets use Router direct-dispatch validation and packet-ledger checks before relay. Reviewer dispatch cards/events may remain registered for legacy intake and historical fixtures, but new runtime cards and next-action text must not present them as required pre-worker approval.

3. **Use recipient-neutral relay checks.**

   The existing result relay checker is already used for PM-bound and Reviewer-bound results. Add or expose a neutral `validate_result_ready_for_recipient_relay` name, then keep the old `validate_result_ready_for_reviewer_relay` name as a compatibility alias until downstream callers are migrated.

4. **Let Router proof cover only mechanical facts.**

   Router proof can replace Reviewer rechecking of target role, envelope identity, hash, relay ledger, and Controller body-boundary facts. Reviewer cards must still require direct inspection of source sufficiency, product usefulness, Worker result quality, PM package completeness, and acceptance risk.

5. **Model first, then update runtime and tests.**

   The model layer must accept the folded PM disposition/release state and reject known-bad shortcuts: raw Worker result to Reviewer, Reviewer gate without PM formal package, PM completion without Reviewer pass, legacy dispatch flag treated as fresh evidence, and Controller body reads.

## Risks / Trade-offs

- **Risk: PM release fold is misread as Reviewer can start earlier.** -> Mitigation: require absorbed disposition plus formal gate package path/hash/scope before any Reviewer gate can pass.
- **Risk: Reviewer stops checking actual quality because Router proof exists.** -> Mitigation: cards and specs say Router proof is mechanical-only; Reviewer still owns quality/source/fact review.
- **Risk: legacy event removal breaks resume or archived fixtures.** -> Mitigation: first mark legacy/compatibility-only and keep aliases; remove only after focused tests and install checks prove there is no active dependency.
- **Risk: background regressions look alive but are not complete.** -> Mitigation: use the repository background log contract and inspect exit/meta artifacts before reporting pass/fail.
- **Risk: other agents modify adjacent files during the run.** -> Mitigation: keep edits scoped, check git status before staging or final sync, and avoid unrelated dirty paths.

## Migration Plan

1. Add OpenSpec specs and focused FlowGuard model obligations for the simplified packet review flow.
2. Update model state/invariants so absorbed PM disposition with a formal gate package satisfies PM release, while direct Reviewer review of raw results remains invalid.
3. Introduce recipient-neutral relay naming and preserve compatibility aliases.
4. Update runtime cards and docs so new flows show Router direct dispatch, PM result disposition, and Reviewer formal package review.
5. Run focused tests and start heavyweight Meta/Capability regressions in background using the required artifact contract.
6. Sync repo-owned FlowPilot assets to the local installed skill, run install audit/check, and create the requested local git version only after validation is current.

## Open Questions

- Whether to remove legacy reviewer-dispatch event names in this change or leave them for a later archive pass after compatibility data is clearer.
- Whether old adoption-log historical text should stay as history or receive a short "superseded by PM package disposition" note in a separate documentation cleanup.
