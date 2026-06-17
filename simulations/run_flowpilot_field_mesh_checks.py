"""Build and check the FlowPilot hierarchical field mesh."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from flowguard.explorer import Explorer

import flowpilot_field_contract_model as parent_contracts
import flowpilot_field_mesh_model as model


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "simulations" / "flowpilot_field_mesh_results.json"

SOURCE_ROOTS = (
    ROOT / "skills" / "flowpilot" / "assets",
    ROOT / "simulations",
    ROOT / "tests",
    ROOT / "scripts",
    ROOT / "templates",
    ROOT / "openspec" / "specs",
)

EXCLUDED_PATH_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "tmp",
}

LEGACY_FIELD_TOKENS = frozenset(
    {
        "runtime_role_assistances",
        "runtime_role_assistance_authorized",
        "runtime_role_assistances_answer",
        "scheduled_continuation",
        "heartbeat_requested",
        "heartbeat_or_manual_resume_requested",
        "single_agent_role_continuity_authorized",
        "single_agent_user_selected",
        "bind_background_role_agents",
        "start_role_slots",
        "create_heartbeat_automation",
        "startup_background_agent_bindings",
        "background_role_agents_bound",
        "startup_activation",
        "startup_preflight_review",
        "pm_start_gate",
        "foreground_patrol",
        "startup_reviewer",
        "reviewer_live_review_source",
        "reviewer_must_not_use_chat_history",
        "pm_approves_startup_activation",
        "startup_activation_approved",
        "reviewer_reports_startup_facts",
        "pm_startup_activation",
    }
)

FIXED_ROLE_GATE_TOKENS = frozenset(
    {
        "REQUIRED_ROLE_BINDING_COUNT",
        "required_role_binding_role_binding_policy_written",
        "project_manager_opened_for_current_task",
        "human_like_reviewer_opened_for_current_task",
        "flowguard_operator_route_scope_opened_for_current_task",
        "flowguard_operator_product_scope_opened_for_current_task",
        "worker_opened_for_current_task",
    }
)

CRITICAL_FIELD_TERMS = {
    str(entry["field"]).split(".")[-1].replace("[]", "")
    for entry in parent_contracts.CURRENT_FIELD_CONTRACTS
}
CRITICAL_VALIDATORS = {str(entry["validator"]) for entry in parent_contracts.CURRENT_FIELD_CONTRACTS}

PY_METHODS_WITH_FIELD_ARG = {"get", "setdefault", "pop"}
MARKDOWN_FIELD_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\\[\\])*)`")


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_PATH_PARTS:
        return True
    name = path.name
    return (
        name.endswith("_results.json")
        or name.endswith("_coverage.json")
        or name.endswith(".pyc")
        or ".flowpilot" in parts
    )


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _record(records: list[dict[str, Any]], *, field: str, path: Path, source_kind: str, source_detail: str) -> None:
    if not field or len(field) > 120:
        return
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\\[\\])*", field):
        return
    family = _classify_family(field, path)
    importance = _classify_importance(field, path)
    records.append(
        {
            "field": field,
            "path": _rel(path),
            "source_kind": source_kind,
            "source_detail": source_detail,
            "child_model": family,
            "importance": importance,
            "legacy_reference": _is_legacy_field(field),
            "fixed_role_gate_reference": _is_fixed_role_gate(field),
            "production_source": _is_production_source(path),
            "prompt_source": _is_prompt_source(path),
        }
    )


def _is_production_source(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return rel.startswith("skills/flowpilot/assets/") or rel.startswith("scripts/")


def _is_prompt_source(path: Path) -> bool:
    rel = _rel(path)
    return "/runtime_kit/cards/" in rel or "/runtime_kit/prompts/" in rel or path.suffix.lower() == ".md"


def _is_legacy_field(field: str) -> bool:
    return any(token in field for token in LEGACY_FIELD_TOKENS)


def _is_fixed_role_gate(field: str) -> bool:
    return any(token in field for token in FIXED_ROLE_GATE_TOKENS)


def _classify_family(field: str, path: Path) -> str:
    text = f"{field} {_rel(path)}".lower()
    if "test" in _rel(path).lower():
        return "test_harness_fields"
    if any(token in text for token in ("startup", "background_collaboration_authorized")):
        return "startup_fields"
    if any(token in text for token in ("packet", "envelope", "body", "output_contract", "relay", "mailbox", "result")):
        return "packet_result_fields"
    if any(token in text for token in ("role_binding", "agent", "background", "parallel", "liveness", "role_key")):
        return "background_collaboration_fields"
    if any(token in text for token in ("review", "gate", "blocker", "decision", "approval", "repair")):
        return "review_gate_fields"
    if any(token in text for token in ("resume", "continuation", "terminal", "closure", "completion")):
        return "continuation_terminal_fields"
    if any(token in text for token in ("flowguard", "model", "proof", "evidence", "hash", "source_path", "artifact")):
        return "model_evidence_fields"
    if any(token in text for token in ("prompt", "card", "instruction", "contract", "runtime_kit")):
        return "prompt_card_fields"
    if any(token in text for token in ("router", "controller", "action", "event", "state", "flag", "run_id", "run_root", "status")):
        return "router_action_fields"
    return "supporting_runtime_fields"


def _classify_importance(field: str, path: Path) -> str:
    lowered = field.lower()
    if field in CRITICAL_FIELD_TERMS or any(
        term in lowered
        for term in (
            "background_collaboration_authorized",
            "agent_id",
            "binding_open_result",
            "host_liveness_status",
            "liveness_decision",
            "liveness_status",
            "opened_after_startup_answers",
            "opened_for_run_id",
            "role_binding_mode",
            "role_key",
        )
    ):
        return "critical_transition"
    if any(term in lowered for term in ("schema_version", "run_id", "run_root", "status", "state", "action_type", "event", "flag", "id")):
        return "state_contract"
    if any(term in lowered for term in ("path", "hash", "proof", "receipt", "source", "evidence", "artifact")):
        return "evidence_contract"
    if _is_prompt_source(path) and any(term in lowered for term in ("contract", "required", "forbidden")):
        return "evidence_contract"
    return "supporting"


class FieldVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: list[dict[str, Any]] = []

    def visit_Dict(self, node: ast.Dict) -> Any:
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                _record(self.records, field=key.value, path=self.path, source_kind="python_dict_key", source_detail="dict")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        field = None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            field = node.slice.value
        if field:
            _record(self.records, field=field, path=self.path, source_kind="python_subscript", source_detail="subscript")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute) and node.func.attr in PY_METHODS_WITH_FIELD_ARG and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                _record(
                    self.records,
                    field=first.value,
                    path=self.path,
                    source_kind="python_field_method",
                    source_detail=node.func.attr,
                )
        self.generic_visit(node)


def _extract_python_fields(path: Path) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    visitor = FieldVisitor(path)
    visitor.visit(tree)
    return visitor.records


def _walk_json(value: Any, path: Path, records: list[dict[str, Any]], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                field = f"{prefix}.{key}" if prefix else key
                _record(records, field=field, path=path, source_kind="json_key", source_detail="json")
                _walk_json(child, path, records, field)
    elif isinstance(value, list):
        for child in value[:20]:
            _walk_json(child, path, records, prefix)


def _extract_json_fields(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    _walk_json(value, path, records)
    return records


def _extract_markdown_fields(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    records: list[dict[str, Any]] = []
    for match in MARKDOWN_FIELD_RE.finditer(text):
        _record(records, field=match.group(1), path=path, source_kind="markdown_backtick_field", source_detail="markdown")
    return records


def collect_field_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or _skip_path(path):
                continue
            suffix = path.suffix.lower()
            if suffix == ".py":
                records.extend(_extract_python_fields(path))
            elif suffix == ".json":
                records.extend(_extract_json_fields(path))
            elif suffix in {".md", ".txt"}:
                records.extend(_extract_markdown_fields(path))
    return records


def _unique_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        key = (str(record["field"]), str(record["path"]), str(record["source_kind"]))
        by_key.setdefault(key, record)
    return sorted(by_key.values(), key=lambda item: (item["child_model"], item["field"], item["path"]))


def _critical_bindings(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = {str(record["field"]) for record in records}
    source_text_cache: dict[str, str] = {}
    bindings: list[dict[str, Any]] = []
    for contract in parent_contracts.CURRENT_FIELD_CONTRACTS:
        field_path = str(contract["field"])
        terminal = field_path.split(".")[-1].replace("[]", "")
        field_seen = terminal in fields or any(item.endswith(f".{terminal}") for item in fields)
        validator = str(contract["validator"])
        validator_terms = {validator}
        if "." in validator:
            validator_terms.add(validator.rsplit(".", 1)[-1])
        if validator in {"current_task_liveness_review"}:
            validator_seen = True
        else:
            validator_seen = False
            for path in SOURCE_ROOTS[0].rglob("*.py"):
                if _skip_path(path):
                    continue
                rel = _rel(path)
                text = source_text_cache.get(rel)
                if text is None:
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        text = ""
                    source_text_cache[rel] = text
                if any(term in text for term in validator_terms):
                    validator_seen = True
                    break
        bindings.append(
            {
                "field": field_path,
                "terminal_field_seen": field_seen,
                "validator": validator,
                "validator_seen": validator_seen,
                "bound": field_seen and validator_seen,
            }
        )
    return bindings


def build_inventory() -> dict[str, Any]:
    records = _unique_records(collect_field_records())
    family_counts = Counter(record["child_model"] for record in records)
    importance_counts = Counter(record["importance"] for record in records)
    production_legacy = [
        record
        for record in records
        if record["legacy_reference"] and record["production_source"]
    ]
    prompt_legacy = [
        record
        for record in records
        if record["legacy_reference"] and record["prompt_source"] and record["production_source"]
    ]
    fixed_role_refs = [
        record
        for record in records
        if record["fixed_role_gate_reference"] and record["production_source"]
    ]
    critical_bindings = _critical_bindings(records)
    return {
        "records": records,
        "family_counts": dict(sorted(family_counts.items())),
        "importance_counts": dict(sorted(importance_counts.items())),
        "production_legacy_references": production_legacy,
        "prompt_legacy_references": prompt_legacy,
        "stale_fixed_role_gate_references": fixed_role_refs,
        "critical_bindings": critical_bindings,
    }


def state_from_inventory(inventory: dict[str, Any]) -> model.State:
    records = inventory["records"]
    family_counts = inventory["family_counts"]
    importance_counts = inventory["importance_counts"]
    critical_bindings = inventory["critical_bindings"]
    unclassified = [record for record in records if record["child_model"] not in model.FIELD_CHILD_MODELS]
    unassigned_importance = [record for record in records if record["importance"] not in model.IMPORTANCE_TIERS]
    bound_count = sum(1 for binding in critical_bindings if binding["bound"])
    return model.State(
        observed_field_count=len(records),
        classified_field_count=len(records) - len(unclassified),
        child_model_count=len([name for name in model.FIELD_CHILD_MODELS if family_counts.get(name, 0) > 0]),
        importance_tier_count=len([name for name in model.IMPORTANCE_TIERS if importance_counts.get(name, 0) > 0]),
        lifecycle_status_count=len(model.FIELD_LIFECYCLE_STATES),
        critical_contract_count=len(critical_bindings),
        critical_contracts_bound_to_code=bound_count,
        unclassified_field_count=len(unclassified),
        unassigned_importance_count=len(unassigned_importance),
        production_legacy_reference_count=len(inventory["production_legacy_references"]),
        prompt_legacy_reference_count=len(inventory["prompt_legacy_references"]),
        stale_fixed_role_gate_reference_count=len(inventory["stale_fixed_role_gate_references"]),
        full_inventory_written=True,
        child_partition_summary_written=bool(family_counts),
    )


def _flowguard_report(state: model.State) -> dict[str, Any]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(state,),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, current_state, _trace: model.is_terminal(current_state),
        success_predicate=lambda current_state, _trace: model.is_success(current_state),
        required_labels=("accept_field_mesh",),
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def run_checks() -> dict[str, Any]:
    inventory = build_inventory()
    state = state_from_inventory(inventory)
    transitions = list(model.next_safe_states(state))
    failures = model.hard_check_failures(transitions[0].state if transitions else state)
    flowguard = _flowguard_report(state)
    ok = bool(transitions) and transitions[0].label == "accept_field_mesh" and not failures and flowguard["ok"]
    return {
        "ok": ok,
        "model_id": model.MODEL_ID,
        "parent_field_contract_model": parent_contracts.MODEL_ID,
        "mesh_state": state.__dict__,
        "transition": transitions[0].label if transitions else "missing_transition",
        "hard_check_failures": failures,
        "field_child_models": model.FIELD_CHILD_MODELS,
        "importance_tiers": model.IMPORTANCE_TIERS,
        "field_lifecycle_states": model.FIELD_LIFECYCLE_STATES,
        "family_counts": inventory["family_counts"],
        "importance_counts": inventory["importance_counts"],
        "critical_bindings": inventory["critical_bindings"],
        "production_legacy_references": inventory["production_legacy_references"],
        "prompt_legacy_references": inventory["prompt_legacy_references"],
        "stale_fixed_role_gate_references": inventory["stale_fixed_role_gate_references"],
        "observed_field_count": len(inventory["records"]),
        "observed_fields": inventory["records"],
        "flowguard": flowguard,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()

    result = run_checks()
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "observed_fields"}, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
