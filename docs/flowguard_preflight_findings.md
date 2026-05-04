# FlowPilot Meta-Process Preflight Findings

Date: 2026-05-04

## Current Finding Set

The active FlowPilot continuation model is heartbeat-only continuation plus
explicit manual resume. The retired external recovery layer is no longer part of
the supported controller, PM, reviewer, heartbeat, installation, or lifecycle
surface.

Current source and runtime checks must preserve these boundaries:

- the project manager may ask for continuation capability evidence, but may not
  require a retired recovery layer before route work can continue;
- the controller wakes only into the packet control plane and must ask PM for a
  `PM_DECISION` before dispatching work;
- the controller may read packet/result envelopes only; packet/result bodies
  are for the addressed role, reviewer, or PM, and controller body access,
  body execution, wrong-role relabelling, hash mismatch acceptance, and stale
  body reuse are control-plane blockers;
- heartbeat/manual resume must load current-run state, execution frontier,
  packet ledger, and role memory before deciding what can proceed;
- reviewer dispatch remains mandatory before existing or fresh worker output is
  used as accepted evidence;
- Cockpit UI unavailability is a startup display-surface fallback, not proof
  that route execution is blocked. If the user requested Cockpit and the UI
  cannot open, PM records the fallback and the reviewer independently verifies
  the display evidence before PM opens the start gate;
- old recovery scripts, prompts, and templates must remain absent from the
  active tree. `scripts/check_install.py` and
  `scripts/audit_local_install_sync.py` both enforce that absence.

## Modeled Risk Boundary

This preflight models the project-control workflow for the `flowpilot` Codex
skill. The current model boundary covers:

- acceptance contract freeze and route creation;
- PM-owned material research packages before product or route decisions can use
  unresolved sources, experiments, mechanisms, or validation claims;
- packet control plane handoff among controller, PM, reviewer, officers, and
  workers;
- route heartbeat/manual resume behavior;
- display-surface startup behavior for Cockpit or chat route signs;
- reviewer factual checks before PM start-gate release;
- child-skill fidelity gates and capability routing;
- terminal closure, final route-wide gate ledgers, and residual-risk review.

## Latest Validation

FlowGuard applicability decision: `use_flowguard`.

Commands run during the 2026-05-04 cleanup and synchronization pass:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts\audit_local_install_sync.py scripts\check_install.py scripts\install_flowpilot.py
python scripts\check_install.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python simulations\run_startup_pm_review_checks.py
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\audit_local_install_sync.py --json
python scripts\install_flowpilot.py --check --json
python scripts\smoke_autopilot.py
```

Results:

- FlowGuard schema version: `1.0`;
- install self-check: passed, including retired-path absence checks;
- local install sync audit: passed, including source-fresh installed skill
  checks;
- meta model: 564071 states, 584243 edges, zero invariant failures, zero stuck
  states, zero nonterminating components;
- capability model: 534893 states, 560353 edges, zero invariant failures, zero
  stuck states, zero nonterminating components;
- startup PM-review model: passed, including hazard detection and safe-graph
  checks;
- smoke autopilot: passed.

## Historical Note

Earlier preflight notes explored a broader recovery architecture. Those notes
are superseded by this file and by the current executable checks. New work must
follow the current finding set above rather than reconstructing retired recovery
behavior from old logs.
