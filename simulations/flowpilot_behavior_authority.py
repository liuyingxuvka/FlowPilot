"""Thin canonical authority lookup for FlowPilot validation models.

The behavior inventory lives only in
``.flowguard/behavior_commitment_ledger/ledger.json``.  This module resolves
one exact commitment for consumers that need stable intent/path identities;
it does not declare or repair behavior rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flowguard import load_behavior_commitment_ledger


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / ".flowguard" / "behavior_commitment_ledger" / "ledger.json"


@dataclass(frozen=True)
class CanonicalBehaviorAuthority:
    commitment_id: str
    business_intent: str
    business_intent_id: str
    behavior_plane: str
    primary_path_id: str
    expected_terminal: str
    source_surface_ids: tuple[str, ...]
    inventory_revision: str


def resolve_behavior_authority(
    commitment_id: str,
    *,
    require_primary_path: bool = True,
) -> CanonicalBehaviorAuthority:
    ledger = load_behavior_commitment_ledger(LEDGER_PATH)
    commitment = next(
        (
            row
            for row in ledger.commitments
            if row.commitment_id == commitment_id
        ),
        None,
    )
    if commitment is None:
        raise KeyError(f"canonical behavior commitment is missing: {commitment_id}")
    path_authority = commitment.path_authority
    primary_path_id = (
        path_authority.primary_path_id if path_authority is not None else ""
    )
    if require_primary_path and not primary_path_id:
        raise ValueError(
            f"canonical behavior commitment lacks one primary path: {commitment_id}"
        )
    return CanonicalBehaviorAuthority(
        commitment_id=commitment.commitment_id,
        business_intent=(
            path_authority.business_intent
            if path_authority is not None and path_authority.business_intent
            else commitment.label
        ),
        business_intent_id=commitment.business_intent_id,
        behavior_plane=commitment.behavior_plane,
        primary_path_id=primary_path_id,
        expected_terminal=commitment.expected_terminal,
        source_surface_ids=commitment.source_surface_ids,
        inventory_revision=ledger.current_revision,
    )


def selected_commitment_id(metadata_key: str) -> str:
    ledger = load_behavior_commitment_ledger(LEDGER_PATH)
    return str(ledger.metadata.get(metadata_key) or "")
