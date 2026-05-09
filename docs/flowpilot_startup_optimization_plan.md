# FlowPilot Startup Optimization Plan

Date: 2026-05-09

## Risk Intent Brief

FlowPilot startup is behavior-bearing control-plane work. The optimization must
reduce startup latency without weakening six-role authority, current-run
continuation binding, reviewer startup fact checking, PM startup activation, or
Controller sealed-body boundaries.

Protected harms:

- a formal run starts work with fewer than the six required role authorities;
- role agents exist but did not receive their current-run core prompt and role
  I/O protocol at startup;
- heartbeat is forgotten, delayed until after long startup work, or bound to the
  wrong run;
- reviewer startup fact review is delayed behind PM prep work or forced to
  re-prove router-owned mechanical facts;
- PM activation opens work before reviewer startup findings and PM prep have
  joined;
- display fallback or host receipts are hidden from reviewer, creating repair
  loops;
- a speed path uses Controller inference or self-attested claims as proof.

Residual blindspot: the startup optimization model is a control-plane model. It
does not prove host-specific subagent spawn or Codex heartbeat UI behavior by
itself; runtime tests and local install checks remain required after code
changes.

## Optimization Sequence

| Order | Optimization | Current Friction | Target Behavior | Acceptance Evidence |
| --- | --- | --- | --- | --- |
| 1 | Merge six-role startup with role-core delivery | `start_role_slots` and `inject_role_core_prompts` are separate bootloader actions | Every role spawn/start receipt also records the role core card path/hash and current role I/O protocol receipt; no later startup core-injection action is needed | `crew_ledger.json`, `role_core_prompt_delivery.json`, and role I/O receipts are written by `start_role_slots`; bootstrap flag `role_core_prompts_injected` is set during the same action |
| 2 | Create heartbeat early when the user allows scheduled continuation | Heartbeat is currently a Controller action after display-plan sync; if later startup gets slow, continuation protection is delayed | After run id and six-role ledger exist, the first Controller action for scheduled continuation is heartbeat creation, before reviewer/PM startup work | `continuation_binding.json` has current run id, one-minute cadence, verified host automation proof, and exists before startup fact-card delivery |
| 3 | Dispatch reviewer startup fact check before PM prep cards | Reviewer fact check currently waits behind several PM card deliveries and user-intake mail | Controller writes mechanical audit and display receipt, then sends `reviewer.startup_fact_check` before PM prep cards; after reviewer card ack, PM prep cards can be delivered while the reviewer report is still pending | Card ledger shows reviewer startup card delivery before PM prep cards; PM activation still waits for reviewer report |
| 4 | Split router-owned mechanical proof from reviewer external facts | Reviewer may get pushed into rechecking facts already proved by the router, while missing direct external receipts such as display fallback | Reviewer receives router-owned proof for mechanical facts, is told not to re-prove them, and receives direct evidence paths for external facts such as display-surface receipt | `startup_mechanical_audit.json` owns mechanical checks; reviewer delivery context includes display evidence; startup report blockers do not cite router-computable facts |
| 5 | Keep system-card batching as a separate future replay-mode change | Barrier bundles exist, but same-role multi-card delivery is not implemented and generic `card_bundle_fold` is rejected today | Do not depend on multi-card body merging for this startup pass; only consider a later batch-envelope feature with per-card receipts and dedicated replay semantics | Existing command-refinement rejection remains valid unless a dedicated replay model and runtime are added |

## Failure Modes The Model Must Catch

| ID | Possible Bug | Required Detection |
| --- | --- | --- |
| B1 | Roles are marked ready but their role core prompt or role I/O protocol was not delivered at spawn/start | Fail if role readiness is recorded without same-action core prompt and current role I/O receipts |
| B2 | A delayed separate role-core injection becomes required before Controller can load | Fail if optimized startup still requires a later core-injection gate |
| B3 | Heartbeat is created before a run id or role ledger exists | Fail if heartbeat proof is not bound to a current run and current role ledger |
| B4 | Heartbeat is delayed until after reviewer/PM startup work | Fail if scheduled continuation is requested and reviewer startup dispatch occurs before heartbeat binding |
| B5 | Heartbeat cadence or host proof is missing/stale | Fail unless cadence is one minute and host proof is verified for the current run |
| B6 | Reviewer fact card is delayed behind PM prep cards | Fail if PM prep starts before reviewer startup fact card dispatch in the optimized plan |
| B7 | PM activation opens before reviewer report and PM prep both join | Fail if `work_beyond_startup_allowed` is true before both prerequisites |
| B8 | Reviewer is asked to re-prove router-owned mechanical facts | Fail if reviewer-required checks include router-owned flags, hashes, or event order |
| B9 | Display fallback host receipt is not visible to reviewer | Fail if reviewer dispatch lacks display-surface direct evidence paths |
| B10 | PM prep blocks reviewer progress instead of running independently after reviewer dispatch | Fail if PM prep starts while reviewer pending without an independence/join policy |
| B11 | Controller reads sealed role bodies or uses self-attested claims as proof | Fail if Controller body access or self-attested proof is present |
| B12 | Startup work proceeds before PM activation | Fail if route/material/product work starts before PM startup activation |

## FlowGuard Coverage

The executable model is `simulations/flowpilot_startup_optimization_model.py`
with runner `simulations/run_flowpilot_startup_optimization_checks.py`.

The model must pass only after:

- the safe optimized sequence reaches terminal success;
- every failure mode above has a hazard state that is detected;
- progress checks show no stuck nonterminal state;
- FlowGuard `Explorer` reachability has no invariant failures.

## Implementation Notes

- Preserve existing dirty work and peer-agent edits. Do not revert unrelated
  modifications.
- Implement one optimization at a time and run targeted tests after each
  behavior-bearing step.
- Long model/test sweeps should run in a background process while local edits or
  shorter targeted checks continue.
- Sync only local surfaces at the end: repository files, local installed
  FlowPilot skill, and local git commit. Do not push to GitHub.
