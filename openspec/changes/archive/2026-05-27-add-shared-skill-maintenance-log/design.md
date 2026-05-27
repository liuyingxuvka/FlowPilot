## Context

FlowPilot already has run-local artifacts for material understanding, activity, skill-improvement observations, and terminal reporting. Those artifacts are useful inside a run, but they do not create a shared Spark-style maintenance index that can be scanned later across skills and workspaces.

The user wants the smallest viable behavior: PM records one shared maintenance row after understanding the task, and then reports that row to Router. This must reuse the existing material-understanding phase instead of creating a new route node or control-plane mechanism.

## Goals / Non-Goals

**Goals:**

- Add one PM-owned bookkeeping step to the material-understanding phase.
- Prefer an existing Spark-style shared skill maintenance log and create the same shared format only when none exists.
- Preserve the log entry reference in `pm_material_understanding.json`.
- Keep the behavior non-gating and lightweight.

**Non-Goals:**

- No Router-owned filesystem search or semantic interpretation.
- No reviewer gate, FlowGuard gate, route node, or terminal acceptance condition.
- No FlowPilot-private maintenance log that competes with the shared Spark-style log.
- No requirement to update the final report path during startup.

## Decisions

1. Put the instruction in `pm_material_understanding`.

   PM has lawful access to the reviewed material and can produce a useful one-line work summary. Startup bootloader and Controller should not guess the task meaning or inspect sealed bodies.

2. Use a shared log fallback path, not a FlowPilot-specific path.

   PM first looks for an existing Spark-style shared skill maintenance log. If none is found, PM creates `.codex/skill_maintenance_log.jsonl` in the workspace root and appends the FlowPilot row there.

3. Router only preserves PM's report.

   Runtime code copies `shared_skill_maintenance_record` from the material-understanding payload into `pm_material_understanding.json`. Router does not validate whether the log path exists or whether the row content is semantically correct.

4. Keep validation narrow.

   A focused FlowGuard model covers the process boundary and known-bad hazards. Ordinary unit coverage verifies the runtime copy-through behavior. Heavyweight Meta/Capability regressions can run in the background for broader confidence, but this feature is intentionally not a new hard gate.

## Risks / Trade-offs

- PM may fail to find a nonstandard existing Spark-style log. Mitigation: the prompt requires PM to report the selected path, and the fallback path is deterministic.
- A malformed log row could exist even when Router records the report. Mitigation: this row is bookkeeping, not acceptance evidence; PM owns semantic quality.
- Extra ceremony could slow startup. Mitigation: the card instructs one row only and forbids creating route nodes or review gates for this bookkeeping step.
