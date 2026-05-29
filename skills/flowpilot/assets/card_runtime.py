"""Public facade for FlowPilot system-card runtime operations.

The focused owner modules keep I/O, ledgers, envelope validation, single-card
ACK handling, and bundle handling separate while this module preserves the
original import surface.
"""

from __future__ import annotations

from card_runtime_ack import (
    _validate_ack_direct_router_fields,
    open_card,
    submit_card_ack,
    validate_card_ack,
)
from card_runtime_bundle import (
    inspect_card_bundle_ack_incomplete,
    open_card_bundle,
    submit_card_bundle_ack,
    validate_card_bundle_ack,
)
from card_runtime_envelopes import (
    _load_bundle_envelope,
    _load_envelope,
    _validate_direct_router_ack_token,
    _validate_target_identity,
)
from card_runtime_io import (
    CARD_ACK_ENVELOPE_SCHEMA,
    CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
    CARD_BUNDLE_ENVELOPE_SCHEMA,
    CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
    CARD_ENVELOPE_SCHEMA,
    CARD_ID_RE,
    CARD_LEDGER_SCHEMA,
    CARD_READ_RECEIPT_SCHEMA,
    RETURN_EVENT_LEDGER_SCHEMA,
    CardRuntimeError,
    project_relative,
    read_json,
    read_json_if_exists,
    resolve_project_path,
    sha256_bytes,
    sha256_file,
    stable_json_hash,
    utc_now,
    write_json,
    _validate_card_id,
)
from card_runtime_ledgers import (
    _ledger_paths,
    _load_card_ledger,
    _load_return_ledger,
    _merge_pending_return_ack,
    _record_terminal_replay_audit,
    _resolved_return_keys,
    _return_has_terminal_proof,
    _return_record_identity,
    _upsert_completed_return_record,
)


__all__ = [
    "CARD_ACK_ENVELOPE_SCHEMA",
    "CARD_BUNDLE_ACK_ENVELOPE_SCHEMA",
    "CARD_BUNDLE_ENVELOPE_SCHEMA",
    "CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA",
    "CARD_ENVELOPE_SCHEMA",
    "CARD_ID_RE",
    "CARD_LEDGER_SCHEMA",
    "CARD_READ_RECEIPT_SCHEMA",
    "RETURN_EVENT_LEDGER_SCHEMA",
    "CardRuntimeError",
    "inspect_card_bundle_ack_incomplete",
    "open_card",
    "open_card_bundle",
    "project_relative",
    "read_json",
    "read_json_if_exists",
    "resolve_project_path",
    "sha256_bytes",
    "sha256_file",
    "stable_json_hash",
    "submit_card_ack",
    "submit_card_bundle_ack",
    "utc_now",
    "validate_card_ack",
    "validate_card_bundle_ack",
    "write_json",
    "_ledger_paths",
    "_load_bundle_envelope",
    "_load_card_ledger",
    "_load_envelope",
    "_load_return_ledger",
    "_merge_pending_return_ack",
    "_record_terminal_replay_audit",
    "_resolved_return_keys",
    "_return_has_terminal_proof",
    "_return_record_identity",
    "_upsert_completed_return_record",
    "_validate_ack_direct_router_fields",
    "_validate_card_id",
    "_validate_direct_router_ack_token",
    "_validate_target_identity",
]
