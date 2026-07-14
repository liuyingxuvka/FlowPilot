# FlowPilot Python Structure Simplification Baseline

Date: 2026-05-17

This note freezes the baseline for the second Python structure simplification
pass. The default goal is maintainability: simplify large Python files while
preserving public entrypoints, command behavior, event names, protocol
semantics, and persisted JSON shapes. If implementation or validation exposes a
real bug, missing loop, stuck path, or model miss, this pass may repair it with
the smallest scoped fix and matching OpenSpec/FlowGuard evidence.

## Baseline

- Working branch: local `main` only.
- Baseline commit: `6e673357c185ce489b54fe0b22723815184cc08c`.
- Local rollback backup: `tmp/maintenance_backup_main_20260517-061157/`.
- Extra local work branches: removed after `codex/behavior-preserving-structural-refactor`
  was fast-forwarded into local `main`.
- OpenSpec change: `simplify-python-structure`.
- FlowGuard decision: `use_flowguard`, mode `model_first_change`, flow type
  `behavior_flow`.

## Structural Hotspots

| File | Approx. Lines | Main Maintenance Concern |
| --- | ---: | --- |
| `skills/flowpilot/assets/flowpilot_router.py` | 38,058 | event/action hotspots remain in a large public Router entrypoint |
| `tests/test_flowpilot_router_runtime.py` | 15,226 | aggregate runtime tests remain difficult to navigate |
| `simulations/capability_model.py` | 8,148 | phase helpers remain large |
| `simulations/meta_model.py` | 7,075 | phase helpers remain large |
| `skills/flowpilot/assets/packet_runtime.py` | 3,678 | schema/path/ledger/relay/session/CLI concerns share one file |
| `scripts/check_install.py` | 1,654 | named check groups still contain heavy bodies |
| `scripts/flowpilot_user_flow_diagram.py` | 1,398 | exact duplicate of the skill asset source |

## Rollback Strategy

- Prefer git history for authoritative rollback.
- Use the local backup directory for manual diff/recovery during this pass.
- Do not add tracked full-file backups of large Python modules.
- Keep original public facades until a future explicit public-entrypoint
  change.

## Required Validation Shape

Run focused checks after each touched boundary. At final completion, run or
inspect:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
openspec validate simplify-python-structure --strict --json
python simulations\run_flowpilot_structural_refactor_checks.py
python scripts\check_install.py --json
python scripts\check_public_release.py --json
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\install_flowpilot.py --check --json
python scripts\audit_local_install_sync.py --json
```

If Meta or Capability model files are touched, run:

```powershell
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python simulations\run_meta_checks.py --full
python simulations\run_capability_checks.py --full
```

The default Meta/Capability commands validate thin-parent routine confidence.
`--full` validates the fast layered full-parent proof and refreshes
`simulations/*_layered_full_results.json`. For background checks, use
`tmp/flowguard_background/` and inspect stdout, stderr, combined, exit, and
metadata artifacts before claiming completion.

## Final Structure Notes

- Source version advanced to `0.9.7` for the local structure simplification
  pass. No tag, remote push, GitHub Release, deploy, or package publication is
  part of this change.
- `scripts/flowpilot_user_flow_diagram.py` is now a thin public wrapper.
- `scripts/check_install.py` is now a thin public entrypoint backed by
  `scripts/install_checks/`.
- `skills/flowpilot/assets/packet_runtime.py` remains the public facade and
  delegates schema, path, contract, ledger, relay, active-holder, session, and
  reviewer responsibilities to focused helper modules.
- `simulations/meta_model.py` and `simulations/capability_model.py` remain the
  parent model entrypoints and delegate phase bodies to focused phase modules.
- Meta and Capability regression evidence is layered. Thin-parent results carry
  routine confidence, and layered full-parent results carry release confidence.
  The current background `run_meta_checks` and
  `run_capability_checks` artifacts both completed with exit `0` from the
  layered `--full` commands.
- Router external-event intake helpers and selected controller action handlers
  now live behind smaller module boundaries while preserving event names and
  persisted state shapes.
- Router runtime split entrypoints now cover all `304` aggregate runtime tests
  exactly once: `0` missing and `0` duplicate `TEST_NAMES`.
- The slow route-mutation runtime domain was verified separately through
  `tmp/flowguard_background/route_mutation_unittest.*` with exit `0`; it ran
  24 tests in 1452.343 seconds.

## Behavior Repair Found During Simplification

Validation exposed several real control-flow gaps while the large files were
being split:

- Explicit runtime event-envelope references could reach startup/current-scope
  reconciliation before the envelope was checked against the current Router
  wait state. The repair validates explicit event envelopes early, so events
  outside the current wait raise a Router error instead of returning a
  recoverable reconciliation wait.
- Research packet relay could be blocked by the worker research-report wait
  that the relay itself must satisfy. The dispatch-recipient gate now models
  formal packet relay output events, so same-obligation relays are not blocked
  by their own expected output wait.
- The former durable material-scan reconciliation could re-raise a known bad
  result envelope before the control-blocker repair path was shown. That
  special material path is now retired; current automatic reconciliation keeps
  invalid ordinary results pending, while explicit event submission still
  hard-rejects them.
- A completed current-node packet could remain active in `packet_ledger.json`
  after the frontier advanced to the next node, causing stale PM-held work to
  block the next node's PM cards. Node completion now closes the current-node
  packet records in the packet ledger.
- Worker-facing packets lacked a clear role-scoped obligation to repair
  in-scope defects before completion, while blanket repair wording would have
  broken reviewer/FlowGuard operator authority boundaries. The prompt repair adds
  role-specific in-scope worker repair, report/model self-correction, and
  reviewer anti-repair wording with planning-quality model coverage.

The event-contract FlowGuard model now contains the same-class hazard
`explicit_envelope_outside_wait_returns_reconciliation_wait`, and the focused
runtime regression is covered by
`test_record_event_rejects_envelope_outside_current_wait`.
