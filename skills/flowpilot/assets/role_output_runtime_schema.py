"""Public facade for role-output runtime schema helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import packet_runtime
from role_output_runtime_schema_authority import (
    _contract_by_id,
    _contract_router_event_mode,
    _current_allowed_external_events,
    validate_direct_router_submission_authority,
)
from role_output_runtime_schema_io import (
    _controller_boundary_sources,
    _json_bytes,
    _json_sha256,
    _manifest_card,
    _project_relative,
    _read_json,
    _registry_path,
    _require_concrete_agent_id,
    _resolve_project_path,
    _run_manifest_path,
    _run_paths,
    _sha256_file,
    _write_json,
    controller_boundary_constraints,
    load_contract_registry,
    utc_now,
)
from role_output_runtime_schema_payload import (
    _choose_placeholder,
    _contract_self_check,
    _deep_merge,
    _get_path,
    _has_path,
    _is_placeholder,
    _path_parts,
    _prior_path_context,
    _required_placeholder,
    _set_path,
)
from role_output_runtime_schema_quality import (
    _catalog_quality_pack_ids,
    _pack_ids_from_payload,
    _quality_pack_catalog_path,
    load_quality_pack_catalog,
    quality_pack_checks_for_run,
)
from role_output_runtime_schema_specs import (
    ATTACHED_QUALITY_PACK_REL_PATHS,
    CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
    CONTROLLER_BOUNDARY_CONFIRMATION_EVENT,
    CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
    CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
    CONTRACT_REGISTRY_PATH,
    FORBIDDEN_CONTROLLER_VISIBLE_BODY_FIELDS,
    OUTPUT_TYPE_SPECS,
    PLACEHOLDER_PREFIXES,
    PROGRESS_MESSAGE_FORBIDDEN_TERMS,
    PROGRESS_MESSAGE_MAX_LEN,
    PROMPT_MANIFEST_SCHEMA,
    QUALITY_PACK_CATALOG_PATH,
    QUALITY_PACK_STATUS_VALUES,
    ROLE_KEYS,
    ROLE_OUTPUT_DIRECT_ROUTER_SUBMISSION_SCHEMA,
    ROLE_OUTPUT_ENVELOPE_SCHEMA,
    ROLE_OUTPUT_LEDGER_SCHEMA,
    ROLE_OUTPUT_RUNTIME_RECEIPT_SCHEMA,
    ROLE_OUTPUT_RUNTIME_SCHEMA,
    ROLE_OUTPUT_RUNTIME_SESSION_SCHEMA,
    ROLE_OUTPUT_STATUS_SCHEMA,
    SUPPORTED_OUTPUT_TYPES,
    OutputTypeSpec,
    RoleOutputRuntimeError,
    _BUILTIN_OUTPUT_TYPE_SPECS,
    _default_contract_registry_path,
    _load_registry_output_type_specs,
    _output_type_specs,
    output_type_spec_source_summary,
    _registry_event_name,
    _registry_text,
    _registry_text_list,
    _role_allowed,
    _spec_for,
    _spec_from_registry_contract,
)

__all__ = tuple(name for name in globals() if not name.startswith("_"))
