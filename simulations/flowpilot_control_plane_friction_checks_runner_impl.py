"""Implementation helpers for the control-plane friction runner."""

from __future__ import annotations

from dataclasses import fields

import flowpilot_control_plane_friction_model as model


def _state_id(state: model.State) -> str:
    """Return a complete deterministic state identity without a shadow schema."""

    return "|".join(
        f"{field.name}={getattr(state, field.name)!r}"
        for field in fields(state)
    )
