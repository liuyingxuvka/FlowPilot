# FlowPilot Terminal Summary Plan

## Purpose

Every formal FlowPilot run should leave a short final summary in the target
workspace. The summary is a terminal receipt, not a new approval gate. It helps
the user and future agents quickly understand what FlowPilot did, and it starts
with a visible FlowPilot project link:

```text
Generated with [FlowPilot](https://github.com/liuyingxuvka/FlowPilot) - a project-control workflow for AI coding agents.
```

## Optimization Checklist

| Step | Optimization | Concrete Change | Done When |
| --- | --- | --- | --- |
| 1 | Model terminal summary behavior first | Extend the router-loop FlowGuard model with terminal-summary states, safe order, and hazards. | Known-bad terminal-summary scenarios fail and the safe scenario passes. |
| 2 | Add a terminal summary action | Before the existing terminal lifecycle action, Router returns a `write_terminal_summary` Controller card when a terminal run lacks a final summary. | Closed, stopped, and cancelled runs ask Controller to write the summary before final terminal observation. |
| 3 | Grant terminal-only read scope | The action explicitly says Controller may read all files under the current run root in terminal summary mode. | The action exposes `read_scope: current_run_root_all_files` and `.flowpilot/runs/<run-id>/**`. |
| 4 | Keep write scope narrow | Controller may only write the summary files and update the run index. | No route, gate, packet, or product files are writable from this action. |
| 5 | Persist Markdown and JSON summaries | Router validates the Controller payload and writes `final_summary.md` plus `final_summary.json`. | Both files exist and include source/read-scope metadata. |
| 6 | Add FlowPilot attribution | The Markdown summary must begin with the FlowPilot GitHub link. | Tests fail if the link is missing or not first. |
| 7 | Register the summary in the index | `.flowpilot/index.json` records `final_summary_path`, `final_summary_json_path`, and `flowpilot_project_url`. | Future agents can find the summary from the index. |
| 8 | Display the same summary to the user | The action requires payload evidence that the exact summary was displayed to the user before apply. | The user sees the final summary and the saved file path is returned. |
| 9 | Sync local install | After repository tests pass, sync the repo-owned FlowPilot skill to the local installed copy. | Local install audit and install check pass. |
| 10 | Commit locally only | Stage and commit the local repository changes without pushing to GitHub. | Local git commit exists; no remote push is performed. |

## Bug-Risk Checklist

| Risk | Why It Matters | FlowGuard/Test Must Catch |
| --- | --- | --- |
| 1. Terminal run exits without a summary | The workspace would still lack the history receipt the user wants. | A completed terminal state without `terminal_summary_written` fails. |
| 2. Summary happens before terminal closure | Controller could read sealed run files before the work is finished. | Summary read scope is invalid unless terminal closure or user stop/cancel is already true. |
| 3. Controller uses terminal read scope to continue route work | The summary mode must not become a back door for approvals or route mutation. | Any route progress, gate approval, or project evidence after summary fails. |
| 4. Summary misses FlowPilot GitHub attribution | The saved artifact loses the discoverability/advertising purpose. | `final_summary.md` without the first-line FlowPilot link fails. |
| 5. Summary is not registered in `.flowpilot/index.json` | Future users/agents cannot find historical summaries. | Summary written without index registration fails. |
| 6. Summary write repeats every terminal tick | Terminal actions could loop or overwrite unnecessarily. | Once `terminal_summary_written` is true, Router proceeds to terminal observation. |
| 7. Summary writes outside allowed files | A simple receipt action could accidentally mutate route state or user outputs. | Write scope outside final summary/index files fails. |
| 8. Stopped/cancelled runs are skipped | User asked for final traces for FlowPilot tasks, not only successful completion. | Stopped and cancelled terminal modes also require summary. |
| 9. Chat display and saved file diverge | User-visible report should match the persisted receipt. | Payload records `displayed_to_user: true` and saved content hash. |
| 10. Existing peer-agent changes are overwritten | Other local AI work must be preserved. | Edits stay scoped; no unrelated file reverts or repo-wide formatters. |

## Intended Implementation Shape

1. Add model fields for terminal summary state:
   - terminal summary card delivered;
   - terminal read-all-run-files authority granted;
   - summary displayed to user;
   - summary Markdown written;
   - summary JSON written;
   - summary registered in index;
   - terminal summary attempted non-summary mutation.

2. Add model transitions:
   - after PM terminal closure, Router delivers terminal summary card;
   - Controller reads all current-run files in terminal summary mode;
   - Controller writes and displays the summary;
   - Router then allows existing terminal lifecycle observation.

3. Add runtime helpers:
   - `_terminal_summary_written(...)`;
   - `_terminal_summary_action(...)`;
   - `_validate_terminal_summary_payload(...)`;
   - `_write_terminal_summary(...)`.

4. Add tests:
   - closed run returns `write_terminal_summary` before `run_lifecycle_terminal`;
   - stopped/cancelled runs also return `write_terminal_summary`;
   - Markdown first line contains the FlowPilot GitHub URL;
   - index records summary paths;
   - repeated terminal action does not request a second summary.

## Validation Plan

Run in this order:

1. `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`
2. `python -m py_compile simulations\flowpilot_terminal_summary_model.py simulations\run_flowpilot_terminal_summary_checks.py`
3. `python simulations\run_flowpilot_terminal_summary_checks.py --json-out simulations\flowpilot_terminal_summary_results.json`
4. Targeted router runtime tests for terminal lifecycle and summary behavior.
5. `python -m py_compile skills\flowpilot\assets\flowpilot_router.py tests\test_flowpilot_router_runtime.py`
6. `python scripts\check_install.py`
7. `python scripts\install_flowpilot.py --sync-repo-owned --json`
8. `python scripts\audit_local_install_sync.py --json`
9. `python scripts\install_flowpilot.py --check --json`

Remote GitHub push is intentionally out of scope for this change.
