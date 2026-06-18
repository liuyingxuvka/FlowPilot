"""Real-issue backfeed registry for FlowPilot replay matrices.

Each row is a public-reference bridge from a discovered issue family into the
fake-AI responder, contract-exhaustion cell space, Cartesian row family, and
runtime replay owner.  The registry deliberately does not copy sealed bodies.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


MODEL_ID = "flowpilot_real_issue_backfeed"
RESULT_PATH = "simulations/flowpilot_real_issue_backfeed_results.json"
REQUIRED_EVIDENCE_OWNER = "real_issue_backfeed_matrix"
RUNTIME_REPLAY_OWNER = "fake_ai_runtime_replay_matrix"

REQUIRED_ROW_FIELDS = (
    "issue_id",
    "source_reference",
    "defect_family",
    "packet_or_result_family",
    "fake_ai_profile_id",
    "contract_cell_id",
    "cartesian_row_id",
    "expected_runtime_reaction",
    "runtime_replay_suite_id",
    "required_evidence_owner",
    "sealed_body_copied",
)


REAL_ISSUE_BACKFEED_ROWS: tuple[dict[str, Any], ...] = (
    {
        "issue_id": "real.contract_surface.acceptance_owner_hidden_rule",
        "source_reference": "run-20260617-152841/events.jsonl:374-412",
        "defect_family": "contract_surface_hidden_semantic_rule",
        "packet_or_result_family": "task.planning",
        "fake_ai_profile_id": "missing_active_id_coverage",
        "contract_cell_id": "fake_ai.projection.missing_active_id_coverage.required_acceptance_item_ids",
        "cartesian_row_id": "cartesian.contract_surface.acceptance_owner_coverage.missing_active_id_coverage",
        "expected_runtime_reaction": "mechanical_reject_reissue_with_missing_ids",
        "runtime_replay_suite_id": RUNTIME_REPLAY_OWNER,
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
    {
        "issue_id": "real.fake_ai.pseudo_json_repeated_reissue",
        "source_reference": "run-20260617-152841/events.jsonl:482,500,518",
        "defect_family": "malformed_result_body",
        "packet_or_result_family": "flowguard_check.post_result",
        "fake_ai_profile_id": "malformed_body.unquoted_keys",
        "contract_cell_id": "fake_ai.raw_body.unquoted_keys",
        "cartesian_row_id": "cartesian.result_body.strict_json.unquoted_keys",
        "expected_runtime_reaction": "mechanical_reject_reissue_with_strict_json_feedback",
        "runtime_replay_suite_id": RUNTIME_REPLAY_OWNER,
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
    {
        "issue_id": "real.review_window.node_acceptance_projection_missing",
        "source_reference": "run-20260617-152841/events.jsonl:536",
        "defect_family": "review_window_material_projection_missing",
        "packet_or_result_family": "review.any_current_subject",
        "fake_ai_profile_id": "reviewer_skips_required_read",
        "contract_cell_id": "review_window.node_acceptance_plan_review.fake_ai.reviewer_skips_required_read",
        "cartesian_row_id": "cartesian.review_window.node_acceptance_plan_review.missing_projection",
        "expected_runtime_reaction": "reviewer_blocker_or_reissue_without_glassbreak_before_threshold",
        "runtime_replay_suite_id": RUNTIME_REPLAY_OWNER,
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
    {
        "issue_id": "real.review_window.projection_member_not_object",
        "source_reference": "run-20260617-152841/events.jsonl:554",
        "defect_family": "review_window_material_projection_type",
        "packet_or_result_family": "review.any_current_subject",
        "fake_ai_profile_id": "reviewer_skips_required_read",
        "contract_cell_id": "review_window.node_acceptance_plan_review.fake_ai.required_read_not_consumed",
        "cartesian_row_id": "cartesian.review_window.node_acceptance_plan_review.projection_member_wrong_type",
        "expected_runtime_reaction": "reviewer_blocker_or_reissue_without_glassbreak_before_threshold",
        "runtime_replay_suite_id": RUNTIME_REPLAY_OWNER,
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
    {
        "issue_id": "real.review_depth.formal_current_contract_only",
        "source_reference": "run-20260617-152841/packets/envelopes/packet-0037.json:24,898",
        "defect_family": "review_window_too_narrow",
        "packet_or_result_family": "review.terminal_backward_replay",
        "fake_ai_profile_id": "reviewer_shallow_pass",
        "contract_cell_id": "review_window.terminal_backward_replay_review.fake_ai.reviewer_shallow_pass",
        "cartesian_row_id": "cartesian.review_window.terminal_backward_replay_review.shallow_pass",
        "expected_runtime_reaction": "reviewer_blocker_or_reissue_without_glassbreak_before_threshold",
        "runtime_replay_suite_id": RUNTIME_REPLAY_OWNER,
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
    {
        "issue_id": "real.singleton.live_evidence_missing_file",
        "source_reference": "live-singleton-audit-required-file-powerset",
        "defect_family": "singleton_live_evidence_missing_required_file",
        "packet_or_result_family": "live_singleton_audit",
        "fake_ai_profile_id": "missing_live_singleton_required_evidence",
        "contract_cell_id": "singleton.live.required_evidence_file_missing",
        "cartesian_row_id": "cartesian.singleton.live.required_file_powerset",
        "expected_runtime_reaction": "evidence_insufficient_not_safe",
        "runtime_replay_suite_id": "singleton_live_evidence_matrix",
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
    },
)


def backfeed_rows() -> tuple[dict[str, Any], ...]:
    return REAL_ISSUE_BACKFEED_ROWS


def backfeed_cells() -> tuple[dict[str, Any], ...]:
    cells: list[dict[str, Any]] = []
    for row in backfeed_rows():
        cells.append(
            {
                "cell_id": f"real_issue_backfeed.{row['issue_id']}",
                "family": str(row["packet_or_result_family"]),
                "contract_family_id": str(row["packet_or_result_family"]),
                "contract_path": str(row["contract_cell_id"]),
                "mutation_kind": str(row["fake_ai_profile_id"]),
                "branch_kind": "real_issue_backfeed",
                "confidence_boundary": "historical_same_class_non_live_control_flow",
                "required_evidence_owner": str(row["required_evidence_owner"]),
                "source_reference": str(row["source_reference"]),
                "defect_family": str(row["defect_family"]),
                "expected_runtime_reaction": str(row["expected_runtime_reaction"]),
                "runtime_replay_suite_id": str(row["runtime_replay_suite_id"]),
                "sealed_body_copied": bool(row["sealed_body_copied"]),
            }
        )
    return tuple(cells)


def backfeed_findings(rows: Iterable[Mapping[str, Any]] | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for row in rows if rows is not None else backfeed_rows():
        issue_id = str(row.get("issue_id") or "")
        for field in REQUIRED_ROW_FIELDS:
            if field not in row or row[field] in ("", None):
                findings.append({"code": "missing_backfeed_field", "issue_id": issue_id, "field": field})
        if row.get("sealed_body_copied") is not False:
            findings.append({"code": "sealed_body_copied_into_backfeed", "issue_id": issue_id})
        if str(row.get("required_evidence_owner") or "") != REQUIRED_EVIDENCE_OWNER:
            findings.append({"code": "wrong_backfeed_owner", "issue_id": issue_id})
        if not str(row.get("runtime_replay_suite_id") or "").endswith("_matrix"):
            findings.append({"code": "missing_runtime_replay_suite", "issue_id": issue_id})
    return findings


def build_report() -> dict[str, Any]:
    rows = list(backfeed_rows())
    cells = list(backfeed_cells())
    findings = backfeed_findings(rows)
    by_family = Counter(str(row["defect_family"]) for row in rows)
    return {
        "ok": not findings,
        "model_id": MODEL_ID,
        "result_path": RESULT_PATH,
        "row_count": len(rows),
        "cell_count": len(cells),
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "sealed_body_copied": False,
        "by_defect_family": dict(sorted(by_family.items())),
        "findings": findings,
        "rows": rows,
        "cells": cells,
    }


def write_report(path: Path | str = RESULT_PATH) -> dict[str, Any]:
    report = build_report()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
