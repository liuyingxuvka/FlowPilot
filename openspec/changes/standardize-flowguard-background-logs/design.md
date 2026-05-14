## Context

FlowPilot has two legacy project-level FlowGuard runners: `run_meta_checks.py` and `run_capability_checks.py`. They build large reachable graphs with local code before printing final JSON sections. They currently preserve final report semantics, but they do not provide live progress while graph construction runs. Agents have also used several log directories, which makes resume and review harder.

## Goals / Non-Goals

**Goals:**
- Standardize the FlowPilot background log directory and final-report evidence rule.
- Add minimal progress output to the two legacy graph builders.
- Keep progress on stderr so stdout final reports remain stable.
- Preserve proof reuse, result JSON shape, and pass/fail logic.

**Non-Goals:**
- No rewrite of the meta or capability models.
- No dependency on a new background-runner framework.
- No broad FlowPilot runtime protocol change.
- No GitHub push until the user approves the push phase.

## Decisions

- Use `tmp/flowguard_background/` as the FlowPilot default background evidence root.
- For each long check, use stable base names such as `run_meta_checks` and `run_capability_checks` with `.out.txt`, `.err.txt`, `.combined.txt`, `.exit.txt`, and `.meta.json`.
- Implement progress inside the existing `_build_reachable_graph` loops because the long wait happens before final reports are printed.
- Use stderr for start/progress/complete/proof-reuse messages and honor `FLOWGUARD_PROGRESS=0`.
- Use the existing `GRAPH_STATE_LIMIT` as a bounded denominator so progress is deterministic and does not require pre-counting the graph.

## Risks / Trade-offs

- [Risk] State-limit-based progress may reach less than `100%` when the reachable graph is smaller than the limit. -> Mitigation: emit an explicit complete line with final state and edge counts.
- [Risk] Progress output could break parsers. -> Mitigation: write progress only to stderr and add tests that stdout stays focused on final report text.
- [Risk] Other active agent edits in FlowPilot may be overwritten. -> Mitigation: modify only `AGENTS.md`, the two legacy runners, and new focused tests/OpenSpec files.
