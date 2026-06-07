# FlowPilot Startup Optimization Plan

Date: 2026-05-09

## Risk Intent Brief

FlowPilot startup is behavior-bearing control-plane work. The optimization must
reduce startup latency without weakening runtime-requested role authority,
current-run continuation binding, startup mechanical audit, PM startup-intake
release, or Controller sealed-body boundaries.

Protected harms:

- a formal run starts work before all current runtime role authorities are bound;
- role bindings exist but did not receive their current-run core prompt and role
  I/O protocol at startup;
- manual-resume binding or lifecycle-guard state is missing after Controller
  core loads;
- startup mechanical audit is delayed behind PM prep work or mixes
  router-owned mechanics with human quality review;
- PM release opens work before the runtime mechanical audit and PM
  node/work-package decision have joined;
- display-surface host receipts are missing from the runtime mechanical audit,
  creating repair loops;
- a speed path uses Controller inference or self-attested claims as proof.

Residual blindspot: the startup optimization model is a control-plane model. It
does not prove host-specific role binding or manual-resume host behavior by
itself; runtime tests and local install checks remain required after code
changes.

## Optimization Sequence

| Order | Optimization | Current Friction | Target Behavior | Acceptance Evidence |
| --- | --- | --- | --- | --- |
| 1 | Bind background role agents with role-core evidence | Startup must not reach Controller work before host-opened current role agents exist | Every role binding receipt records the role core card path/hash and current role I/O protocol receipt; no later startup core-injection action is needed | `role_binding_ledger.json`, role memory packets, and role I/O receipts are written by `bind_background_role_agents`; bootstrap flag `background_role_agents_bound` is set during the same action |
| 2 | Record manual-resume binding after Controller core | FlowPilot no longer creates scheduled-continuation or heartbeat automation | After Controller core loads, the run records current lifecycle-guard plus stable manual-resume launcher evidence | `continuation_binding.json` has current run id, `mode=manual_resume`, lifecycle guard evidence, and no heartbeat automation fields |
| 3 | Run runtime mechanical audit before PM prep cards | Startup facts can be delayed behind PM card deliveries and user-intake mail | Controller writes mechanical audit and display receipt before PM prep cards; PM prep cards can start only after Router exposes the released `user_intake` mail | Action ledger shows `write_startup_mechanical_audit` before PM startup-intake release; PM release waits for the mechanical audit |
| 4 | Keep reviewer out of startup mechanical release | Reviewer may get pushed into rechecking facts already proved by the router, while missing later human-quality review duties | Runtime owns startup path/hash/display/run/role mechanics; Reviewer only reviews substantive artifacts, worker results, and human-quality gates after real work exists | `startup_mechanical_audit.json` owns mechanical checks; human-review startup-release blockers are absent from the current contract |
| 5 | Keep system-card batching as a separate future replay-mode change | Barrier bundles exist, but same-role multi-card delivery is not implemented and generic `card_bundle_fold` is rejected today | Do not depend on multi-card body merging for this startup pass; only consider a later batch-envelope feature with per-card receipts and dedicated replay semantics | Existing command-refinement rejection remains valid unless a dedicated replay model and runtime are added |

## Failure Modes The Model Must Catch

| ID | Possible Bug | Required Detection |
| --- | --- | --- |
| B1 | Roles are marked ready but their role core prompt or role I/O protocol was not delivered at startup binding | Fail if role readiness is recorded without same-action core prompt and current role I/O receipts |
| B2 | A delayed separate role-core injection becomes required before Controller can load | Fail if optimized startup still requires a later core-injection gate |
| B3 | Startup reaches Controller without current background agent bindings | Fail if Controller loads before `background_role_agents_bound` and role I/O receipts |
| B4 | Manual-resume binding is missing after Controller core | Fail if continuation binding is not current-run manual resume with lifecycle guard evidence |
| B5 | Old heartbeat or scheduled-continuation automation is recreated | Fail if startup emits heartbeat automation actions or heartbeat fields |
| B6 | Runtime mechanical audit is delayed behind PM prep cards | Fail if PM prep starts before `write_startup_mechanical_audit` in the optimized plan |
| B7 | PM release opens before mechanical audit and PM prep both join | Fail if `work_beyond_startup_allowed` is true before both prerequisites |
| B8 | Reviewer is asked to re-prove router-owned mechanical facts | Fail if startup-release checks require reviewer-owned flags, hashes, or event order |
| B9 | Display-surface host receipt is not visible to Runtime/Router | Fail if mechanical audit lacks display-surface direct evidence paths |
| B10 | PM prep blocks runtime audit progress instead of running independently after audit completion | Fail if PM prep waits on a human-review startup card instead of runtime audit evidence |
| B11 | Controller reads sealed role bodies or uses self-attested claims as proof | Fail if Controller body access or self-attested proof is present |
| B12 | Startup work proceeds before PM release | Fail if route/material/product work starts before PM startup-intake release |

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
