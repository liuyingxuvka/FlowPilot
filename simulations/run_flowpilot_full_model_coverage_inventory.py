"""Build a repository-wide FlowGuard model coverage inventory.

This inventory consumes the read-only coverage sweep and the current
model-test alignment report. It does not execute model runners or tests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP_PATH = ROOT / "simulations" / "flowpilot_full_model_coverage_sweep_results.json"
DEFAULT_ALIGNMENT_PATH = ROOT / "simulations" / "flowpilot_model_test_alignment_results.json"
DEFAULT_REPLAY_EVIDENCE_PATH = ROOT / "simulations" / "flowpilot_full_model_replay_evidence.json"
DEFAULT_JSON_OUT = ROOT / "simulations" / "flowpilot_full_model_coverage_inventory_results.json"
DEFAULT_MARKDOWN_OUT = ROOT / "docs" / "flowpilot_full_model_coverage_inventory.md"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _runner_from_script(script: str) -> str:
    name = Path(script).stem
    if name.startswith("run_"):
        name = name[4:]
    if name.endswith("_checks"):
        name = name[:-7]
    return name


def _alignment_runner_keys(alignment: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for plan in alignment.get("per_plan") or []:
        if not isinstance(plan, dict):
            continue
        for command in plan.get("model_checks") or []:
            if not isinstance(command, str):
                continue
            parts = command.split()
            for part in parts:
                if part.startswith("simulations/") or part.startswith("simulations\\"):
                    keys.add(_runner_from_script(part))
    return keys


def _source_audited_runner_keys(alignment: dict[str, Any]) -> set[str]:
    keys = _alignment_runner_keys(alignment)
    if alignment.get("source_audit_ok") is not None:
        keys.add("flowpilot_model_test_alignment")
    source_plan = alignment.get("source_contract_plan", {}).get("plan", {})
    for evidence in source_plan.get("test_evidence") or []:
        if not isinstance(evidence, dict):
            continue
        command = str(evidence.get("command") or "")
        for part in command.split():
            if part.startswith("simulations/") or part.startswith("simulations\\"):
                keys.add(_runner_from_script(part))
    return keys


def _test_corpus() -> str:
    test_root = ROOT / "tests"
    return "\n".join(_read_text(path) for path in sorted(test_root.rglob("*.py")))


def _ordinary_test_reference_strength(
    *,
    runner: str,
    script: str,
    test_text: str,
    source_audited_runners: set[str],
) -> str:
    if runner in source_audited_runners:
        return "source_audited_alignment"
    script_stem = Path(script).stem
    tokens = {
        runner,
        script_stem,
        runner.removeprefix("flowpilot_"),
        runner.replace("_", "-"),
    }
    if any(token and token in test_text for token in tokens):
        return "ordinary_test_text_reference"
    return "none_detected"


def _finding_count_by_class(findings: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        key = str(finding.get("classification") or "unclassified")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _read_replay_evidence(path: Path = DEFAULT_REPLAY_EVIDENCE_PATH) -> dict[str, dict[str, Any]]:
    try:
        raw = _read_json(path)
    except FileNotFoundError:
        return {}
    entries: dict[str, dict[str, Any]] = {}
    for entry in raw.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        runner = str(entry.get("runner") or "")
        if runner:
            entries[runner] = entry
    return entries


def _covered_skipped_checks(record: dict[str, Any], replay_evidence: dict[str, dict[str, Any]]) -> set[str]:
    runner = str(record.get("runner") or "")
    entry = replay_evidence.get(runner) or {}
    covered = entry.get("covered_skipped_checks") if isinstance(entry.get("covered_skipped_checks"), dict) else {}
    return {
        str(key)
        for key, value in covered.items()
        if isinstance(value, dict)
        and value.get("status") == "covered_elsewhere"
        and value.get("evidence_ids")
    }


def _gap_classes(
    record: dict[str, Any],
    reference_strength: str,
    replay_evidence: dict[str, dict[str, Any]],
) -> list[str]:
    classes: list[str] = []
    if not record.get("parsed"):
        classes.append("runner_unparsed_or_unavailable")
    if record.get("parsed") and record.get("ok") is False:
        classes.append("runner_not_ok")
    findings = record.get("findings") or []
    finding_classes = {str(item.get("classification") or "") for item in findings if isinstance(item, dict)}
    if "modeled_current_live_hit_fix_runtime_or_current_state" in finding_classes:
        classes.append("live_runtime_or_state_findings")
    if "modeled_source_hit_fix_source_or_runtime" in finding_classes:
        classes.append("source_or_code_findings")
    skipped_checks = record.get("skipped_checks") or {}
    covered_skipped = _covered_skipped_checks(record, replay_evidence)
    blocking_skipped_checks = {
        key: value
        for key, value in skipped_checks.items()
        if key != "default_results_file"
        and str(key) not in covered_skipped
        and not str(value).startswith("covered_elsewhere:")
    }
    if blocking_skipped_checks:
        classes.append("skipped_or_scoped_evidence")
        if any("replay" in str(key) or "replay" in str(value) for key, value in blocking_skipped_checks.items()):
            classes.append("missing_or_scoped_replay_adapter")
    sections = record.get("sections") or {}
    has_live_or_source = bool(sections.get("live", {}).get("present") or sections.get("source", {}).get("present"))
    if reference_strength == "none_detected" and not has_live_or_source:
        classes.append("abstract_without_detected_ordinary_test_reference")
    if record.get("coverage_tier") == "unclassified_model_tier":
        classes.append("unclassified_model_tier")
    if not classes:
        classes.append("currently_consumable_inventory_evidence")
    return classes


def _group_records(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for record in records:
        for gap in record["gap_classes"]:
            groups.setdefault(gap, []).append(record["runner"])
    return {key: sorted(value) for key, value in sorted(groups.items())}


def build_inventory(
    *,
    sweep_path: Path = DEFAULT_SWEEP_PATH,
    alignment_path: Path = DEFAULT_ALIGNMENT_PATH,
    replay_evidence_path: Path = DEFAULT_REPLAY_EVIDENCE_PATH,
) -> dict[str, Any]:
    sweep = _read_json(sweep_path)
    alignment = _read_json(alignment_path)
    replay_evidence = _read_replay_evidence(replay_evidence_path)
    test_text = _test_corpus()
    source_audited_runners = _source_audited_runner_keys(alignment)

    records: list[dict[str, Any]] = []
    for raw in sweep.get("runners") or []:
        if not isinstance(raw, dict):
            continue
        runner = str(raw.get("runner") or "")
        script = str(raw.get("script") or "")
        reference_strength = _ordinary_test_reference_strength(
            runner=runner,
            script=script,
            test_text=test_text,
            source_audited_runners=source_audited_runners,
        )
        findings = [item for item in raw.get("findings") or [] if isinstance(item, dict)]
        records.append(
            {
                "runner": runner,
                "script": script,
                "coverage_tier": raw.get("coverage_tier"),
                "read_only_mode": raw.get("read_only_mode"),
                "ok": raw.get("ok"),
                "parsed": raw.get("parsed"),
                "ordinary_test_reference_strength": reference_strength,
                "sections": raw.get("sections") or {},
                "finding_count": len(findings),
                "finding_counts": _finding_count_by_class(findings),
                "skipped_checks": raw.get("skipped_checks") or {},
                "covered_skipped_checks": sorted(_covered_skipped_checks(raw, replay_evidence)),
                "replay_evidence": replay_evidence.get(runner) or {},
                "gap_classes": _gap_classes(raw, reference_strength, replay_evidence),
                "metadata": raw.get("metadata") or {},
            }
        )

    groups = _group_records(records)
    priority_order = (
        "runner_unparsed_or_unavailable",
        "runner_not_ok",
        "live_runtime_or_state_findings",
        "source_or_code_findings",
        "missing_or_scoped_replay_adapter",
        "skipped_or_scoped_evidence",
        "abstract_without_detected_ordinary_test_reference",
        "unclassified_model_tier",
    )
    prioritized_groups = [
        {
            "gap_class": gap,
            "runner_count": len(groups.get(gap, [])),
            "runners": groups.get(gap, []),
        }
        for gap in priority_order
        if gap in groups
    ]

    return {
        "schema_version": "flowpilot.full_model_coverage_inventory.v1",
        "result_type": "flowpilot_full_model_coverage_inventory",
        "read_only": True,
        "sweep_path": sweep_path.relative_to(ROOT).as_posix(),
        "alignment_path": alignment_path.relative_to(ROOT).as_posix(),
        "replay_evidence_path": replay_evidence_path.relative_to(ROOT).as_posix()
        if replay_evidence_path.exists()
        else None,
        "runner_count": len(records),
        "sweep_ok": bool(sweep.get("ok")),
        "alignment_ok": bool(alignment.get("ok")),
        "source_audit_ok": bool(alignment.get("source_audit_ok")),
        "full_coverage_ok": bool(alignment.get("full_coverage_ok")),
        "release_convergence_ok": bool(alignment.get("release_convergence_ok")),
        "finding_count": sum(int(record["finding_count"]) for record in records),
        "gap_class_counts": {item["gap_class"]: item["runner_count"] for item in prioritized_groups},
        "coverage_tier_counts": sweep.get("coverage_tier_counts") or {},
        "classification_counts": sweep.get("classification_counts") or {},
        "prioritized_groups": prioritized_groups,
        "records": sorted(records, key=lambda item: item["runner"]),
        "claim_boundary": (
            "This inventory proves that FlowGuard model/check entrypoints were "
            "enumerated and classified against current evidence. Scoped replay "
            "or skipped checks remain blocking unless the replay evidence "
            "manifest attaches them to exact current runtime or source evidence."
        ),
    }


def _markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(rows[0]) + " |\n"
    sep = "| " + " | ".join("---" for _ in rows[0]) + " |\n"
    body = "".join("| " + " | ".join(row) + " |\n" for row in rows[1:])
    return header + sep + body


def write_markdown(report: dict[str, Any], path: Path) -> None:
    rows = [["Gap class", "Runner count", "First runners"]]
    for group in report["prioritized_groups"]:
        runners = group["runners"]
        first = ", ".join(runners[:8])
        if len(runners) > 8:
            first += f", ... (+{len(runners) - 8})"
        rows.append([group["gap_class"], str(group["runner_count"]), first])

    not_ok = [record for record in report["records"] if record["ok"] is False or not record["parsed"]]
    not_ok_rows = [["Runner", "Issue", "Mode", "Notes"]]
    for record in not_ok:
        issue = "unparsed" if not record["parsed"] else "not_ok"
        notes = "; ".join(record["gap_classes"])
        not_ok_rows.append([record["runner"], issue, str(record["read_only_mode"]), notes])
    if "abstract_without_detected_ordinary_test_reference" in report["gap_class_counts"]:
        abstract_note = (
            "- `abstract_without_detected_ordinary_test_reference` is the main queue "
            "for future focused boundary-test planning.\n"
        )
    else:
        abstract_note = (
            "- `abstract_without_detected_ordinary_test_reference` is not present in "
            "the current inventory; baseline missing ordinary-test references are now "
            "owned by the focused coverage-gap tests.\n"
        )

    text = (
        "# FlowPilot Full FlowGuard Model Coverage Inventory\n\n"
        "## Claim Boundary\n\n"
        f"{report['claim_boundary']}\n\n"
        "## Summary\n\n"
        f"- Runner count: `{report['runner_count']}`\n"
        f"- Sweep ok: `{str(report['sweep_ok']).lower()}`\n"
        f"- Model-test alignment ok: `{str(report['alignment_ok']).lower()}`\n"
        f"- Source audit ok: `{str(report['source_audit_ok']).lower()}`\n"
        f"- Full coverage ok: `{str(report['full_coverage_ok']).lower()}`\n"
        f"- Release convergence ok: `{str(report['release_convergence_ok']).lower()}`\n"
        f"- Finding count across sweep records: `{report['finding_count']}`\n\n"
        "## Prioritized Gap Groups\n\n"
        + _markdown_table(rows)
        + "\n## Not-OK Or Unparsed Runners\n\n"
        + _markdown_table(not_ok_rows)
        + "\n## Evidence Notes\n\n"
        "- `source_audited_alignment` means the runner is consumed by the current "
        "FlowGuard model-test alignment plan.\n"
        "- `ordinary_test_text_reference` is weaker: it means the test corpus "
        "mentions the runner/model key, not necessarily that every boundary is asserted.\n"
        + abstract_note
        + "- `missing_or_scoped_replay_adapter` means a replay gap is still blocking "
        "unless `covered_skipped_checks` attaches it to exact replay evidence.\n"
        + "- `supporting_model_owned` means the runner is an explicitly registered "
        "supporting model tier, not an unknown model boundary.\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP_PATH)
    parser.add_argument("--alignment-json", type=Path, default=DEFAULT_ALIGNMENT_PATH)
    parser.add_argument("--replay-evidence-json", type=Path, default=DEFAULT_REPLAY_EVIDENCE_PATH)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN_OUT)
    args = parser.parse_args()

    report = build_inventory(
        sweep_path=args.sweep_json,
        alignment_path=args.alignment_json,
        replay_evidence_path=args.replay_evidence_json,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown_out:
        write_markdown(report, args.markdown_out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
