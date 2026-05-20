"""Runtime kit contract-index lookup helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACT_INDEX_PATH = Path(__file__).resolve().parent / "runtime_kit" / "contracts" / "contract_index.json"


def load_contract_index(path: Path | None = None) -> dict[str, Any]:
    source = path or CONTRACT_INDEX_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def contract_selection_rules(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    index = load_contract_index(path)
    rules = index.get("selection_rules")
    if not isinstance(rules, list):
        raise ValueError("contract index selection_rules must be a list")
    return tuple(rule for rule in rules if isinstance(rule, dict))


def contract_selection_rules_by_task_family(path: Path | None = None) -> dict[str, dict[str, Any]]:
    rules_by_family: dict[str, dict[str, Any]] = {}
    for rule in contract_selection_rules(path):
        task_family = str(rule.get("task_family") or "")
        if task_family:
            rules_by_family[task_family] = dict(rule)
    return rules_by_family


def contract_id_for_task_family(task_family: str, path: Path | None = None) -> str:
    rule = contract_selection_rules_by_task_family(path).get(task_family)
    if not rule:
        raise KeyError(task_family)
    return str(rule.get("contract_id") or "")


__all__ = (
    "CONTRACT_INDEX_PATH",
    "load_contract_index",
    "contract_selection_rules",
    "contract_selection_rules_by_task_family",
    "contract_id_for_task_family",
)
