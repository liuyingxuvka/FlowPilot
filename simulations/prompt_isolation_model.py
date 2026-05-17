"""Compatibility facade for the FlowPilot prompt-isolation model."""

from __future__ import annotations

from typing import Iterable

from flowguard import Workflow

from prompt_isolation_model_hazards import hazard_states
from prompt_isolation_model_invariants import INVARIANTS, invariant_failures, prompt_isolation_invariant
from prompt_isolation_model_state import Action, State, Tick, Transition, initial_state
from prompt_isolation_model_transitions import PromptIsolationStep, next_safe_states


def build_workflow() -> Workflow:
    return Workflow((PromptIsolationStep(),), name="flowpilot_prompt_isolation")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 90


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "PromptIsolationStep",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
    "next_safe_states",
    "prompt_isolation_invariant",
]
