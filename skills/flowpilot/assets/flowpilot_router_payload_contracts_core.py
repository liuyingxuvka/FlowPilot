"""Core payload-contract helper."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_catalog import *

def _payload_contract(
    *,
    name: str,
    required_object: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    allowed_values: dict[str, list[Any]] | None = None,
    conditional_required_fields: dict[str, list[str]] | None = None,
    structural_requirements: list[str] | None = None,
    description: str,
    reviewer_check: str | None = None,
) -> dict[str, Any]:
    contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": name,
        "required_object": required_object,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "conditional_required_fields": conditional_required_fields or {},
        "structural_requirements": structural_requirements or [],
        "allowed_values": allowed_values or {},
        "description": description,
        "controller_may_fill_missing_fields": False,
        "on_missing_or_ambiguous_payload": "ask_user_or_return_to_named_role; do_not_guess",
    }
    if reviewer_check:
        contract["reviewer_check"] = reviewer_check
    return contract

__all__ = ("_payload_contract",)
