# Verification

## Preflight Checks

Run:

```powershell
python simulations/run_startup_pm_review_checks.py
python simulations/run_card_instruction_coverage_checks.py
python simulations/run_command_refinement_checks.py
python simulations/run_flowpilot_event_contract_checks.py
python simulations/run_flowpilot_event_capability_registry_checks.py
python simulations/run_flowpilot_route_replanning_policy_checks.py --json-out simulations/flowpilot_route_replanning_policy_results.json
python simulations/run_flowpilot_controller_break_glass_checks.py --json-out simulations/flowpilot_controller_break_glass_results.json
python simulations/run_flowpilot_structure_maintenance_checks.py --json-out simulations/flowpilot_structure_maintenance_results.json
python simulations/run_flowpilot_router_facade_split_checks.py --json-out simulations/flowpilot_router_facade_split_results.json
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
python simulations/run_release_tooling_checks.py
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
python scripts/check_install.py
python scripts/audit_local_install_sync.py
python scripts/smoke_flowpilot.py
```

For maintenance that touches the split router/runtime/model structure, also use
`docs/flowpilot_final_structure_verification_matrix.md`. That matrix maps
touched facades and domain files to focused commands and to the background log
contract under `tmp/flowguard_background/`.
The StructureMesh/TestMesh maintenance check is the current executable gate for
router split ownership, child-model facade ownership, and slow-suite evidence
visibility.
The router-facade split check is the current executable gate for PromptStore,
prompt asset integrity, prompt-delivery/card-delivery ownership, Controller
ledger helper ownership, and role-output protocol helper ownership.
The Model-Test Alignment check is the current executable map between major
FlowGuard model obligations and ordinary test evidence. A green alignment report
means each declared obligation has current passing evidence for the required
test kinds; it is not a substitute for the model runner or production replay.

The tier runner can execute the router domain suites without loading the unsupported
aggregate implementation file as the routine source of truth:

```powershell
python scripts/run_test_tier.py --tier router-route --background --background-dir tmp/flowguard_background --background-max-parallel 4 --json
python scripts/run_test_tier.py --tier router --background --background-dir tmp/flowguard_background --json
```

`router-route` composes focused route-mutation runtime child suites for draft
activation, model-miss triage, acceptance repair, preconditions, transactions,
topology, sibling replacement, and parent backward replay. The aggregate
`tests.router_runtime.route_mutation` module remains an explicit historical
aggregate, not routine parent evidence.

On Windows, the tier runner starts background children and foreground child
commands with hidden subprocess windows. Completion evidence still comes from
the artifact set in `tmp/flowguard_background/`, not from visible console
windows or progress output. Re-running the same background suite clears the old
artifact set before launch, so a stale `.exit.txt` cannot be reused as current
completion evidence.

Expected:

- zero invariant failures;
- zero missing required labels;
- zero progress findings;
- zero stuck states;
- reachable success.
- FlowPilot release tooling cannot publish or package companion skills.
- execution frontier and visible Codex plan sync labels are present before
  behavior-bearing work.
- startup runtime-intake checks reject shadow routes, report-only reviewer
  startup bypasses, background-collaboration authorization gaps, and any work
  before PM startup intake release.
- card instruction coverage checks reject cards that lack role identity,
  `required_return`, `next_step_source`, router-return wording, or
  role-appropriate action guidance.
- command refinement checks preserve the original multi-command startup
  baseline and permit only the safe internal `run-until-wait` startup fold;
  higher-risk card, relay, startup mechanical-audit card, and role-output folds remain
  rejected until they have dedicated conformance replay.
- event contract checks reject internal Router actions, unknown strings, direct
  ACK/check-in events, false-prerequisite waits, success-only material repair
  outcome tables, duplicate repair side effects, and post-write-only cleanup as
  legal persisted role waits.
- event capability registry checks reject registered-but-not-currently-executable
  waits, wrong producer roles, parent/module repairs that target leaf-only
  events, and repair outcome tables that collapse success, blocker, and
  protocol-blocker rows onto one event.
- route replanning policy checks reject planning/root/parent node-entry gaps
  being converted into repair nodes before executable child work, while still
  allowing post-work reviewer failures to use repair/mutation paths.

Route-local models under `.flowpilot/task-models/` belong to an adopted target
project's runtime evidence. They should be checked when present in that target
project, but this public package check does not require this repository's
private development `.flowpilot/` state.

## Install Checks

Run:

```powershell
python scripts/install_flowpilot.py --check
python scripts/audit_local_install_sync.py
python scripts/check_install.py
```

Expected:

- real FlowGuard import works;
- `flowpilot.dependencies.json` parses;
- required project files exist;
- required dependencies are installed and fresh; missing optional companion
  skills are reported as warnings rather than blocking the FlowPilot package
  check;
- `skills/flowpilot/SKILL.md` exists and declares `name: flowpilot`;
- reusable FlowPilot templates exist;
- simulation scripts exist;
- template JSON files parse.
- `templates/flowpilot/execution_frontier.template.json` parses.
- repository-owned installed skills are source-fresh;
- installed skill names are unique, so stale backup skills cannot shadow the
  active FlowPilot skill;
- the unsupported Cockpit prototype is absent from the active source tree before a
  from-scratch UI restart.
- If local `.flowpilot/` runtime state exists, its main JSON files parse.

## Public Release Check

Run before publishing this repository:

```powershell
python scripts/check_public_release.py
```

Expected:

- tracked files do not include `.flowpilot/`, private `.flowguard/` state,
  `kb/`, local environment files, caches, or secret-shaped content; the exact
  four-file public Behavior Commitment Ledger source/model allowlist under
  `.flowguard/behavior_commitment_ledger/` is permitted, while every other
  `.flowguard/` path remains rejected;
- the dependency manifest parses and has explicit sources for GitHub-backed
  dependencies;
- external dependency `SKILL.md` links are reachable when URL checking is not
  skipped;
- release tooling reports FlowPilot repository scope only and no companion
  publishing authority;
- validation commands pass.

If companion skill GitHub URLs are intentionally not filled in yet, the public
release check should block and report those missing sources. The user decides
whether and when to publish or update those companion skill repositories.

## Smoke Checks

Run:

```powershell
python scripts/smoke_flowpilot.py
```

For shorter runs or timeout diagnosis, list and run smoke groups:

```powershell
python scripts/smoke_flowpilot.py --list-groups
python scripts/smoke_flowpilot.py --fast --group core
python scripts/smoke_flowpilot.py --fast --group friction
python scripts/smoke_flowpilot.py --fast --group daemon
python scripts/smoke_flowpilot.py --fast --group parents
python scripts/smoke_flowpilot.py --fast --group structure
python scripts/smoke_flowpilot.py --fast --group topology
```

Group boundaries:

- `core`: card instruction coverage, release tooling, startup PM review,
  command refinement, reviewer challenge, and prompt isolation.
- `friction`: control-plane and cross-plane friction checks.
- `daemon`: persistent router daemon, daemon startup lock, controller actions,
  wait liveness, terminal projection, and control transaction registry.
- `parents`: model mesh, meta, capability, and hierarchy checks.
- `structure`: structure maintenance, router facade split, similarity
  convergence, and model-test alignment.
- `topology`: project topology orientation, build, and check.

Expected:

- release tooling simulation passes;
- meta simulation passes;
- capability simulation passes.
- startup runtime-intake simulation passes.
- card instruction coverage simulation passes.

## Startup Runtime Intake Release Check

For an active target project after route, state, frontier, role-binding memory,
continuation, and visible-plan evidence have been written, Runtime/Router must
check the real startup mechanical facts and write
`.flowpilot/runs/<run-id>/startup/startup_mechanical_audit.json` plus its proof.

The mechanical audit is not PM approval. It must check startup intake authority,
no chat-history startup-intake substitution, user authorization versus actual
state, route/state/frontier consistency, requested old-route or old-asset
cleanup, manual-resume lifecycle evidence, runtime role-binding evidence,
display status, and shadow or residual route state. If the audit has blockers,
PM sends remediation back to authorized workers through a packet and requires a
fresh mechanical audit.

After the project manager releases startup intake from the current clean
mechanical audit, PM writes
`.flowpilot/runs/<run-id>/startup/pm_startup_intake_decision.json` and updates
state plus frontier with `work_beyond_startup_allowed: true`.

Expected:

- `.flowpilot/current.json` resolves to the active run and
  `.flowpilot/index.json` records that run;
- current-run `state.json`, `execution_frontier.json`, and
  `routes/<active-route>/flow.json`
  agree on the same active nonterminal route;
- old top-level control state is absent, unsupported-only, or quarantined and is
  not used as current state;
- continuing prior work has a current-run prior-work import packet;
- `role_binding_ledger.json` is current for that route and required role memory
  packets are present and current;
- continuation records current manual-resume or foreground-duty evidence with
  no heartbeat automation claim;
- startup role-binding evidence records current-run live bindings for
  runtime-required roles after user authorization, or a structured stop/blocker
  when the host cannot open the requested background or parallel role surface;
- `startup_runtime_intake_release.startup_mechanical_audit` records a clean
  runtime mechanical audit;
- `startup_runtime_intake_release.pm_startup_intake_release` records the
  project manager's release decision based on that audit;
- `startup_runtime_intake_release` in state and frontier records the hard gate
  and sets `work_beyond_startup_allowed: true`.

If the mechanical audit is blocked or PM has not released startup intake,
FlowPilot must
not run child skills, image generation, implementation, route chunks, or
completion work. A route-local file without matching canonical
state/frontier/role-binding/continuation evidence is a shadow route, not a
recoverable partial pass.

## Lifecycle Currentness Check

Run:

```powershell
python scripts/flowpilot_lifecycle.py --root . --mode scan --write-record --json
```

Expected:

- the active route, latest manual-resume or foreground-duty evidence, state,
  and execution frontier are loaded;
- current routes record that no heartbeat automation is current authority;
- stale Codex automations are reported as required pause actions rather than
  accepted as FlowPilot liveness;
- terminal routes write inactive lifecycle state back to state/frontier
  evidence before completion is claimed.

## Lifecycle Reconciliation Check

Before pausing, restarting, or closing a formal route, run a unified lifecycle
inventory:

```powershell
python scripts/flowpilot_lifecycle.py --root . --mode pause --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode restart --write-record --json
python scripts/flowpilot_lifecycle.py --root . --mode terminal --write-record --json
```

Use the mode that matches the lifecycle operation. The command is read-only
except for writing `.flowpilot/runs/<run-id>/lifecycle/latest.json` and events.
It does not change Codex automations. If it reports stale automation pause
actions, complete them through the official Codex app automation interface,
then rerun the inventory before claiming pause, restart, or terminal cleanup.

Expected:

- local state, execution frontier, current lifecycle evidence, and any stale
  Codex automation pause actions are all represented;
- local state/frontier lifecycle fields agree with the intended operation;
- `.flowpilot/runs/<run-id>/lifecycle/latest.json` exists for the latest lifecycle operation.
