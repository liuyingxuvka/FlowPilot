"""Thin adapter for the canonical FlowPilot behavior commitment ledger."""

from pathlib import Path

from flowguard import load_behavior_commitment_ledger


LEDGER_PATH = Path(__file__).with_name("ledger.json")


def build_behavior_commitment_ledger():
    """Load the sole machine-readable behavior inventory."""

    return load_behavior_commitment_ledger(LEDGER_PATH)

