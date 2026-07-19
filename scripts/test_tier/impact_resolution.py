"""Current-contract owner impact planning for FlowPilot test evidence.

The canonical repository snapshot is provenance only.  Evidence applicability
is decided exclusively from each owner's explicit command and covered inputs.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform
import shlex
import sys
from typing import Any, Iterable, Literal, Mapping, Sequence

from flowguard import (
    ProofArtifactRef,
    TestResultReuseTicket,
    proof_artifact_gap_codes,
)

from .command_builders import TierCommand
from .source_fingerprint import file_fingerprint, fingerprint_set, source_snapshot


ROOT = Path(__file__).resolve().parents[2]
IMPACT_PLAN_SCHEMA_VERSION = "flowpilot.test_impact_plan.v1"
EVIDENCE_MANIFEST_SCHEMA_VERSION = "flowpilot.acceptance_testmesh_evidence_manifest.v4"
FLOWGUARD_BACKGROUND_WRAPPER = (
    ROOT / "scripts" / "run_flowguard_background.py"
).resolve()

# These dynamically imported control-plane inputs do not appear in the static
# import closure.  Each therefore names one exact current full owner.  Other
# control-plane files are owned through their ordinary import/MTA edges.
SHARED_CONTROL_PLANE_INPUTS = frozenset(
    {
        "scripts/run_test_tier.py",
        "scripts/test_tier/command_builders.py",
        "scripts/test_tier/fast_commands.py",
        "scripts/test_tier/mta_evidence_commands.py",
    }
)
SHARED_CONTROL_PLANE_OWNER = {
    "scripts/run_test_tier.py": "test_tier_runner",
    "scripts/test_tier/command_builders.py": "test_tier_runner",
    "scripts/test_tier/fast_commands.py": "test_tier_runner",
    "scripts/test_tier/mta_evidence_commands.py": "model_test_alignment_tests",
}

# Some repository entrypoints extend sys.path before importing an asset package,
# so the ordinary repository-root import closure cannot resolve those edges.
# Keep those exceptions explicit and bind each input only to commands that
# actually execute or test it.
EXPLICIT_DYNAMIC_INPUT_OWNERS = {
    "skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py": frozenset(
        {
            "complete_workstream_fake_ai_execution_receipts",
            "formal_ai_submit_adversarial_runner",
            "formal_ai_submit_adversarial_tests",
        }
    ),
    "simulations/run_flowpilot_model_mesh_checks.py": frozenset(
        {
            "mta_evidence_test_flowpilot_model_mesh_coverage_receipts_6c11f605fb1c",
        }
    ),
    "skills/flowpilot/.skillguard/check-manifest.json": frozenset(
        {
            "flowguard_skillguard_current_contract",
        }
    ),
    "skills/flowpilot/.skillguard/compiled-contract.json": frozenset(
        {
            "flowguard_skillguard_current_contract",
        }
    ),
}

# These closure owners each publish one model-level proof consumed by the
# release ModelMesh.  MTA supplies behavior obligations for ordinary test
# owners; these three process owners instead have one explicit release
# obligation apiece.  Keep the binding here with owner identity so execution
# and reuse receipts cannot omit or guess the obligation later.
EXPLICIT_OWNER_OBLIGATION_IDS = {
    "behavior_commitment_risk_current_evidence": frozenset(
        {"model-receipt:flowpilot_053_ppa_maintenance"}
    ),
    "current_contract_cartesian_current_evidence": frozenset(
        {"model-receipt:flowpilot_current_contract_cartesian_matrix"}
    ),
    "model_test_alignment_current_evidence": frozenset(
        {"model-receipt:flowpilot_model_test_alignment"}
    ),
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class OwnerContract:
    owner_id: str
    command: tuple[str, ...]
    covered_inputs: tuple[str, ...]
    covered_obligation_ids: tuple[str, ...] = ()
    covered_evidence_ids: tuple[str, ...] = ()
    dependency_owner_ids: tuple[str, ...] = ()
    owner_kind: Literal["tier_command", "shared_control_plane"] = "tier_command"

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "command": list(self.command),
            "covered_inputs": list(self.covered_inputs),
            "covered_obligation_ids": list(self.covered_obligation_ids),
            "covered_evidence_ids": list(self.covered_evidence_ids),
            "dependency_owner_ids": list(self.dependency_owner_ids),
            "owner_kind": self.owner_kind,
        }


@dataclass(frozen=True, slots=True)
class OwnerIdentity:
    command_fingerprint: str
    test_source_fingerprint: str
    tested_artifact_fingerprint: str
    dependency_fingerprints: Mapping[str, str]
    environment_fingerprint: str
    covered_input_fingerprint: str
    covered_input_fingerprints: Mapping[str, str]
    covered_obligation_ids: tuple[str, ...]
    covered_evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_fingerprint": self.command_fingerprint,
            "test_source_fingerprint": self.test_source_fingerprint,
            "tested_artifact_fingerprint": self.tested_artifact_fingerprint,
            "dependency_fingerprints": dict(sorted(self.dependency_fingerprints.items())),
            "environment_fingerprint": self.environment_fingerprint,
            "covered_input_fingerprint": self.covered_input_fingerprint,
            "covered_input_fingerprints": dict(
                sorted(self.covered_input_fingerprints.items())
            ),
            "covered_obligation_ids": list(self.covered_obligation_ids),
            "covered_evidence_ids": list(self.covered_evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class OwnerDecision:
    owner_id: str
    action: Literal["reuse", "execute", "blocked"]
    reason_codes: tuple[str, ...]
    identity: OwnerIdentity
    previous_proof_artifact_id: str = ""
    reuse_ticket: TestResultReuseTicket | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "action": self.action,
            "reason_codes": list(self.reason_codes),
            "identity": self.identity.to_dict(),
            "previous_proof_artifact_id": self.previous_proof_artifact_id,
            "reuse_ticket": (
                self.reuse_ticket.to_dict() if self.reuse_ticket is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ImpactPlan:
    plan_id: str
    requested_scope: str
    snapshot: Mapping[str, Any]
    previous_manifest_path: str
    previous_manifest_sha256: str
    seed_baseline: bool
    contracts: tuple[OwnerContract, ...]
    decisions: tuple[OwnerDecision, ...]
    blockers: tuple[str, ...]

    @property
    def executable_owner_ids(self) -> tuple[str, ...]:
        return tuple(
            decision.owner_id
            for decision in self.decisions
            if decision.action == "execute"
        )

    @property
    def reused_owner_ids(self) -> tuple[str, ...]:
        return tuple(
            decision.owner_id
            for decision in self.decisions
            if decision.action == "reuse"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": IMPACT_PLAN_SCHEMA_VERSION,
            "plan_id": self.plan_id,
            "requested_scope": self.requested_scope,
            "snapshot": dict(self.snapshot),
            "previous_manifest": {
                "path": self.previous_manifest_path,
                "sha256": self.previous_manifest_sha256,
            },
            "seed_baseline": self.seed_baseline,
            "contracts": [contract.to_dict() for contract in self.contracts],
            "decisions": [decision.to_dict() for decision in self.decisions],
            "blockers": list(self.blockers),
            "execute_owner_ids": list(self.executable_owner_ids),
            "reuse_owner_ids": list(self.reused_owner_ids),
        }


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _portable_path(value: str) -> str:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"<external>/{resolved.parent.name}/{resolved.name}"


def _portable_command(values: Sequence[Any]) -> str:
    parts = [str(value) for value in values]
    if parts:
        try:
            if Path(parts[0]).resolve() == Path(sys.executable).resolve():
                parts[0] = "python"
        except OSError:
            pass
    return " ".join(parts)


def _existing_repo_file(value: str) -> Path | None:
    candidate = Path(value.split("::", 1)[0])
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _existing_repo_directory_files(value: str) -> tuple[Path, ...]:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return ()
    if not resolved.is_dir():
        return ()
    return tuple(
        sorted(
            path.resolve()
            for path in resolved.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".py", ".md", ".json"}
        )
    )


def _module_file(value: str) -> Path | None:
    parts = value.split(".")
    for end in range(len(parts), 0, -1):
        candidate = ROOT.joinpath(*parts[:end]).with_suffix(".py")
        if candidate.is_file():
            return candidate.resolve()
        package = ROOT.joinpath(*parts[:end], "__init__.py")
        if package.is_file():
            return package.resolve()
    return None


def _command_direct_inputs(command: Sequence[str]) -> tuple[Path, ...]:
    if len(command) < 2:
        raise ValueError("unsupported_owner_command_shape")
    output_value_indexes = {
        index + 1
        for index, value in enumerate(command[:-1])
        if str(value) == "--json-out"
    }
    files: set[Path] = set()
    for index, value in enumerate(command[1:], start=1):
        if index in output_value_indexes:
            continue
        direct = _existing_repo_file(str(value))
        if direct is not None:
            files.add(direct)
        files.update(_existing_repo_directory_files(str(value)))
        module_path = _module_file(str(value))
        if module_path is not None:
            files.add(module_path)

    if "-m" in command:
        module_index = command.index("-m") + 1
        module_name = str(command[module_index]) if module_index < len(command) else ""
        values = command[module_index + 1 :]
        if module_name not in {"pytest", "unittest"}:
            module_path = _module_file(module_name)
            if module_path is not None:
                files.add(module_path)
        skip_next = False
        for value in values:
            text = str(value)
            if skip_next:
                skip_next = False
                continue
            if text in {"-k", "--json-out", "--timeout-seconds", "--budget-seconds"}:
                skip_next = True
                continue
            if text.startswith("-"):
                continue
            direct = _existing_repo_file(text)
            if direct is not None:
                files.add(direct)
                continue
            module_path = _module_file(text)
            if module_path is not None:
                files.add(module_path)

    if not files:
        raise ValueError("unsupported_owner_command_shape")
    return tuple(sorted(files))


def _resolve_import(module: str) -> Path | None:
    if not module:
        return None
    candidate = ROOT.joinpath(*module.split(".")).with_suffix(".py")
    if candidate.is_file():
        return candidate.resolve()
    package = ROOT.joinpath(*module.split("."), "__init__.py")
    if package.is_file():
        return package.resolve()
    for base in (ROOT / "scripts", ROOT / "simulations", ROOT / "skills" / "flowpilot" / "assets"):
        candidate = base.joinpath(*module.split(".")).with_suffix(".py")
        if candidate.is_file():
            return candidate.resolve()
        package = base.joinpath(*module.split("."), "__init__.py")
        if package.is_file():
            return package.resolve()
    return None


@lru_cache(maxsize=None)
def _direct_local_imports(path_text: str) -> tuple[Path, ...]:
    path = Path(path_text)
    if path.suffix != ".py":
        return ()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ()
    imported_paths: set[Path] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        for module in modules:
            imported = _resolve_import(module)
            if imported is not None:
                imported_paths.add(imported)
    return tuple(sorted(imported_paths))


def _import_closure(paths: Iterable[Path]) -> set[Path]:
    found = {path.resolve() for path in paths}
    pending = list(found)
    while pending:
        path = pending.pop()
        for imported in _direct_local_imports(str(path)):
            if imported not in found:
                found.add(imported)
                pending.append(imported)
    return found


def _owner_import_closure(
    command: Sequence[str],
    direct_inputs: Sequence[Path],
) -> set[Path]:
    """Keep a nested model owner separate from its shared execution wrapper."""

    direct = {path.resolve() for path in direct_inputs}
    command_entry = _existing_repo_file(str(command[1])) if len(command) > 1 else None
    if command_entry != FLOWGUARD_BACKGROUND_WRAPPER:
        return _import_closure(direct)
    nested_inputs = direct - {FLOWGUARD_BACKGROUND_WRAPPER}
    return {FLOWGUARD_BACKGROUND_WRAPPER} | _import_closure(nested_inputs)


@lru_cache(maxsize=1)
def _flowguard_background_wrapper_import_inputs() -> frozenset[str]:
    """Return infrastructure formerly inherited by every wrapped payload."""

    return frozenset(
        _relative(path)
        for path in _import_closure((FLOWGUARD_BACKGROUND_WRAPPER,))
        if path != FLOWGUARD_BACKGROUND_WRAPPER
    )


def _mta_supplements(
    direct_command_inputs: Mapping[str, set[str]],
    commands: Mapping[str, TierCommand],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    simulations = str(ROOT / "simulations")
    if simulations not in sys.path:
        sys.path.insert(0, simulations)
    from flowpilot_model_test_alignment_source_code_contracts import (  # type: ignore
        source_code_contracts,
    )
    from flowpilot_model_test_alignment_source_test_evidence import (  # type: ignore
        source_test_evidence,
    )
    from flowpilot_model_test_alignment_common import (  # type: ignore
        configure_execution_evidence,
    )
    from flowpilot_model_test_alignment_family_plans import (  # type: ignore
        build_alignment_plan_entries,
    )

    contracts = {
        contract.code_contract_id: contract
        for contract in source_code_contracts()
    }
    configure_execution_evidence(
        None,
        declaration_only=True,
        evidence_scope="routine",
    )
    declared_evidence = [
        evidence
        for entry in build_alignment_plan_entries()
        for evidence in entry["plan"].test_evidence
    ]
    declared_evidence.extend(source_test_evidence())
    path_additions: dict[str, set[str]] = {
        owner_id: set() for owner_id in direct_command_inputs
    }
    obligation_additions: dict[str, set[str]] = {
        owner_id: set() for owner_id in direct_command_inputs
    }
    evidence_additions: dict[str, set[str]] = {
        owner_id: set() for owner_id in direct_command_inputs
    }

    def selected_evidence_ids(owner_id: str) -> tuple[str, ...]:
        command = commands[owner_id].command
        return tuple(
            str(command[index + 1])
            for index, value in enumerate(command[:-1])
            if value == "--evidence-id"
        )

    def selects_test(owner_id: str, evidence_id: str, test_name: str) -> bool:
        command = commands[owner_id].command
        if "--collect-only" in command:
            return False
        explicit_evidence_ids = selected_evidence_ids(owner_id)
        if explicit_evidence_ids:
            return evidence_id in explicit_evidence_ids
        explicit_nodes = [
            str(value)
            for value in command
            if "::" in str(value)
        ]
        if explicit_nodes:
            return any(test_name in value for value in explicit_nodes)
        filters = [
            str(command[index + 1])
            for index, value in enumerate(command[:-1])
            if value == "-k"
        ]
        if filters:
            return any(value in test_name for value in filters)
        return True

    for evidence in declared_evidence:
        evidence_path = str(evidence.path).replace("\\", "/")
        explicit_candidates = [
            owner_id
            for owner_id in direct_command_inputs
            if evidence.evidence_id in selected_evidence_ids(owner_id)
        ]
        if evidence_path.startswith("tests/"):
            candidates = [
                owner_id
                for owner_id, inputs in direct_command_inputs.items()
                if evidence_path in inputs
                and not selected_evidence_ids(owner_id)
                and selects_test(
                    owner_id,
                    evidence.evidence_id,
                    evidence.test_name,
                )
            ]
        else:
            declared_command = tuple(shlex.split(evidence.command))
            candidates = [
                owner_id
                for owner_id, command in commands.items()
                if not selected_evidence_ids(owner_id)
                and tuple(command.command[1:]) == declared_command[1:]
            ]
        selected = (
            explicit_candidates
            if len(explicit_candidates) == 1
            else candidates
            if not explicit_candidates and len(candidates) == 1
            else []
        )
        if len(selected) != 1:
            continue
        owner_id = selected[0]
        path_additions[owner_id].add(evidence_path)
        obligation_additions[owner_id].update(evidence.covered_obligations)
        evidence_additions[owner_id].add(evidence.evidence_id)
        for contract_id in evidence.covered_code_contracts:
            contract = contracts.get(contract_id)
            if contract is not None and contract.path:
                path_additions[owner_id].add(str(contract.path).replace("\\", "/"))
    return path_additions, obligation_additions, evidence_additions


@lru_cache(maxsize=32)
def _build_owner_contracts_cached(
    tier_commands: tuple[TierCommand, ...],
) -> tuple[OwnerContract, ...]:
    """Build exact owner inputs from current commands plus proven MTA edges."""

    seen: set[str] = set()
    direct_by_owner: dict[str, set[str]] = {}
    closure_by_owner: dict[str, set[str]] = {}
    command_by_owner: dict[str, TierCommand] = {}
    for command in tier_commands:
        if command.name in seen:
            raise ValueError(f"duplicate_owner_id:{command.name}")
        seen.add(command.name)
        direct = _command_direct_inputs(command.command)
        direct_by_owner[command.name] = {_relative(path) for path in direct}
        closure = (
            set(direct)
            if "--collect-only" in command.command
            else _owner_import_closure(command.command, direct)
        )
        closure_by_owner[command.name] = {_relative(path) for path in closure}
        command_by_owner[command.name] = command
    mta_paths, mta_obligations, mta_evidence_ids = _mta_supplements(
        direct_by_owner,
        command_by_owner,
    )
    for path, owner_id in SHARED_CONTROL_PLANE_OWNER.items():
        if owner_id in closure_by_owner:
            closure_by_owner[owner_id].add(path)
    for path, owner_ids in EXPLICIT_DYNAMIC_INPUT_OWNERS.items():
        for owner_id in owner_ids:
            if owner_id in closure_by_owner:
                closure_by_owner[owner_id].add(path)
    return tuple(
        OwnerContract(
            owner_id=owner_id,
            command=command_by_owner[owner_id].command,
            covered_inputs=tuple(
                sorted(closure_by_owner[owner_id] | mta_paths[owner_id])
            ),
            covered_obligation_ids=tuple(
                sorted(
                    mta_obligations[owner_id]
                    | set(EXPLICIT_OWNER_OBLIGATION_IDS.get(owner_id, ()))
                )
            ),
            covered_evidence_ids=tuple(sorted(mta_evidence_ids[owner_id])),
        )
        for owner_id in sorted(command_by_owner)
    )


def build_owner_contracts(
    tier_commands: Sequence[TierCommand],
) -> tuple[OwnerContract, ...]:
    """Return cached immutable owner contracts for one exact command set."""

    return _build_owner_contracts_cached(tuple(tier_commands))


def owner_identity(contract: OwnerContract) -> OwnerIdentity:
    covered: dict[str, str] = {}
    missing: list[str] = []
    for relative in contract.covered_inputs:
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        covered[relative] = file_fingerprint(path)
    if missing:
        raise FileNotFoundError("owner_inputs_missing:" + ",".join(sorted(missing)))
    tests = {path: value for path, value in covered.items() if path.startswith("tests/")}
    artifacts = {
        path: value for path, value in covered.items() if not path.startswith("tests/")
    }
    environment = {
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    return OwnerIdentity(
        command_fingerprint=_sha256_json(list(contract.command)),
        test_source_fingerprint=fingerprint_set(tests),
        tested_artifact_fingerprint=fingerprint_set(artifacts),
        dependency_fingerprints={"covered_inputs": fingerprint_set(covered)},
        environment_fingerprint=_sha256_json(environment),
        covered_input_fingerprint=fingerprint_set(covered),
        covered_input_fingerprints=covered,
        covered_obligation_ids=contract.covered_obligation_ids,
        covered_evidence_ids=contract.covered_evidence_ids,
    )


def _proof_from_row(row: Mapping[str, Any]) -> ProofArtifactRef | None:
    value = row.get("proof_artifact")
    if not isinstance(value, Mapping):
        return None
    try:
        return ProofArtifactRef(**dict(value))
    except (TypeError, ValueError):
        return None


def _identity_matches(row: Mapping[str, Any], current: OwnerIdentity) -> bool:
    value = row.get("identity")
    return isinstance(value, Mapping) and dict(value) == current.to_dict()


def _execution_wrapper_scope_reduction(
    row: Mapping[str, Any],
    current: OwnerIdentity,
) -> tuple[str, ...]:
    """Prove that a former wrapper-import superset can reuse payload evidence."""

    previous = row.get("identity")
    if not isinstance(previous, Mapping):
        return ()
    for key in (
        "command_fingerprint",
        "environment_fingerprint",
        "covered_obligation_ids",
        "covered_evidence_ids",
    ):
        if previous.get(key) != current.to_dict()[key]:
            return ()
    previous_inputs = previous.get("covered_input_fingerprints")
    if not isinstance(previous_inputs, Mapping):
        return ()
    current_inputs = current.covered_input_fingerprints
    if (
        FLOWGUARD_BACKGROUND_WRAPPER.relative_to(ROOT).as_posix()
        not in current_inputs
        or not set(current_inputs) < set(previous_inputs)
        or any(previous_inputs.get(path) != value for path, value in current_inputs.items())
    ):
        return ()
    dropped = tuple(sorted(set(previous_inputs) - set(current_inputs)))
    if not set(dropped) <= _flowguard_background_wrapper_import_inputs():
        return ()
    return dropped


def _current_reuse_ticket(
    owner_id: str,
    row: Mapping[str, Any],
    current: OwnerIdentity,
    *,
    reason: str = "all exact owner applicability identities remain current",
    metadata: Mapping[str, Any] | None = None,
) -> TestResultReuseTicket | None:
    proof = _proof_from_row(row)
    if proof is None:
        return None
    proof_gaps = proof_artifact_gap_codes(
        proof,
        declared_status=str(row.get("result_status") or ""),
        required_obligation_ids=current.covered_obligation_ids,
        require_result_path=True,
        require_fingerprints=True,
    )
    if proof_gaps:
        return None
    if (
        proof.result_status != "passed"
        or proof.exit_code != 0
        or not proof.current
        or not proof.route_evidence_current
        or proof.progress_only
        or proof.stale_reasons
    ):
        return None
    result_fingerprint = str(
        row.get("result_fingerprint")
        or proof.metadata.get("result_fingerprint")
        or ""
    )
    if not result_fingerprint:
        return None
    return TestResultReuseTicket(
        evidence_id=owner_id,
        previous_evidence_id=proof.artifact_id,
        reason=reason,
        same_output_proof_id=proof.artifact_id,
        command_fingerprint=current.command_fingerprint,
        test_source_fingerprint=current.test_source_fingerprint,
        tested_artifact_fingerprint=current.tested_artifact_fingerprint,
        dependency_fingerprints=current.dependency_fingerprints,
        environment_fingerprint=current.environment_fingerprint,
        result_fingerprint=result_fingerprint,
        covered_obligation_ids=current.covered_obligation_ids,
        metadata={
            "covered_input_fingerprint": current.covered_input_fingerprint,
            "previous_proof_artifact_id": proof.artifact_id,
            **dict(metadata or {}),
        },
    )


def load_previous_manifest(
    path: Path | None,
    *,
    expected_sha256: str,
    seed_baseline: bool,
) -> tuple[dict[str, Any] | None, str, tuple[str, ...]]:
    if seed_baseline:
        if path is not None or expected_sha256:
            return None, "", ("seed_baseline_cannot_name_previous_manifest",)
        return None, "", ()
    if path is None or not expected_sha256:
        return None, "", ("previous_manifest_identity_required",)
    if not path.is_file():
        return None, "", ("previous_manifest_missing",)
    actual = sha256_file(path)
    if actual != expected_sha256:
        return None, actual, ("previous_manifest_sha256_mismatch",)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, actual, ("previous_manifest_invalid_json",)
    if not isinstance(value, dict):
        return None, actual, ("previous_manifest_not_object",)
    if value.get("schema_version") != EVIDENCE_MANIFEST_SCHEMA_VERSION:
        return None, actual, ("previous_manifest_not_current_v4",)
    return value, actual, ()


def resolve_impact(
    *,
    requested_scope: str,
    tier_commands: Sequence[TierCommand],
    all_owner_contracts: Sequence[OwnerContract],
    previous_manifest: Mapping[str, Any] | None,
    previous_manifest_path: str = "",
    previous_manifest_sha256: str = "",
    seed_baseline: bool = False,
    preexisting_blockers: Sequence[str] = (),
) -> ImpactPlan:
    contracts = build_owner_contracts(tier_commands)
    snapshot = source_snapshot()
    blockers = list(preexisting_blockers)
    previous_snapshot = (
        previous_manifest.get("snapshot")
        if isinstance(previous_manifest, Mapping)
        else None
    )
    previous_files = (
        previous_snapshot.get("files")
        if isinstance(previous_snapshot, Mapping)
        else {}
    )
    if not isinstance(previous_files, Mapping):
        previous_files = {}
        blockers.append("previous_snapshot_inventory_missing")
    current_files = snapshot["files"]
    assert isinstance(current_files, Mapping)
    changed_paths = {
        path
        for path in set(previous_files) | set(current_files)
        if previous_files.get(path) != current_files.get(path)
    } if previous_manifest is not None else set()

    global_owners_by_path: dict[str, set[str]] = {}
    for contract in all_owner_contracts:
        for path in contract.covered_inputs:
            global_owners_by_path.setdefault(path, set()).add(contract.owner_id)
    previous_owners_for_mapping = (
        previous_manifest.get("owners")
        if isinstance(previous_manifest, Mapping)
        else {}
    )
    if isinstance(previous_owners_for_mapping, Mapping):
        for owner_id, row in previous_owners_for_mapping.items():
            identity = row.get("identity") if isinstance(row, Mapping) else None
            covered_inputs = (
                identity.get("covered_input_fingerprints")
                if isinstance(identity, Mapping)
                else None
            )
            if not isinstance(covered_inputs, Mapping):
                continue
            for path in covered_inputs:
                global_owners_by_path.setdefault(str(path), set()).add(
                    str(owner_id)
                )
    unmapped = sorted(
        path
        for path in changed_paths
        if path not in global_owners_by_path
    )
    blockers.extend(f"impact_mapping_missing:{path}" for path in unmapped)
    previous_owners = (
        previous_manifest.get("owners")
        if isinstance(previous_manifest, Mapping)
        else {}
    )
    if not isinstance(previous_owners, Mapping):
        previous_owners = {}
        if previous_manifest is not None:
            blockers.append("previous_owner_rows_missing")
    checkpoint_reuse_only = (
        isinstance(previous_manifest, Mapping)
        and previous_manifest.get("manifest_kind") == "flowpilot.owner_checkpoint"
        and previous_manifest.get("claim_scope") == "owner_reuse_only"
    )
    if checkpoint_reuse_only:
        requested_owner_ids = {contract.owner_id for contract in contracts}
        missing_checkpoint_owner_ids = sorted(
            requested_owner_ids - {str(owner_id) for owner_id in previous_owners}
        )
        blockers.extend(
            f"checkpoint_owner_out_of_scope:{owner_id}"
            for owner_id in missing_checkpoint_owner_ids
        )

    decisions: list[OwnerDecision] = []
    for contract in contracts:
        identity = owner_identity(contract)
        reasons: list[str] = []
        action: Literal["reuse", "execute", "blocked"]
        ticket: TestResultReuseTicket | None = None
        previous_proof_id = ""
        if blockers:
            action = "blocked"
            reasons.extend(blockers)
        elif seed_baseline:
            action = "execute"
            reasons.append("current_v4_baseline_seed")
        else:
            previous_row = previous_owners.get(contract.owner_id)
            if not isinstance(previous_row, Mapping):
                action = "execute"
                reasons.append("current_owner_proof_missing")
            else:
                proof = _proof_from_row(previous_row)
                previous_proof_id = proof.artifact_id if proof is not None else ""
                dropped_wrapper_inputs = _execution_wrapper_scope_reduction(
                    previous_row,
                    identity,
                )
                if _identity_matches(previous_row, identity):
                    ticket = _current_reuse_ticket(
                        contract.owner_id,
                        previous_row,
                        identity,
                    )
                    reuse_reason = "exact_owner_proof_reused"
                elif dropped_wrapper_inputs:
                    ticket = _current_reuse_ticket(
                        contract.owner_id,
                        previous_row,
                        identity,
                        reason=(
                            "payload inputs are unchanged after transferring shared "
                            "execution-wrapper imports to their exact infrastructure owner"
                        ),
                        metadata={
                            "dropped_execution_wrapper_inputs": list(
                                dropped_wrapper_inputs
                            ),
                            "scope_reduction_kind": (
                                "flowguard_background_execution_wrapper_transfer"
                            ),
                        },
                    )
                    reuse_reason = "execution_wrapper_scope_reduction_reused"
                else:
                    ticket = None
                    reuse_reason = ""
                if ticket is not None:
                    action = "reuse"
                    reasons.append(reuse_reason)
                elif dropped_wrapper_inputs or _identity_matches(previous_row, identity):
                    action = "execute"
                    reasons.append("current_owner_reuse_proof_invalid")
                else:
                    action = "execute"
                    reasons.append("owner_applicability_identity_changed")
        decisions.append(
            OwnerDecision(
                owner_id=contract.owner_id,
                action=action,
                reason_codes=tuple(sorted(set(reasons))),
                identity=identity,
                previous_proof_artifact_id=previous_proof_id,
                reuse_ticket=ticket,
            )
        )

    plan_payload = {
        "requested_scope": requested_scope,
        "snapshot_fingerprint": snapshot["fingerprint"],
        "previous_manifest_sha256": previous_manifest_sha256,
        "seed_baseline": seed_baseline,
        "contracts": [contract.to_dict() for contract in contracts],
        "decisions": [
            {
                "owner_id": decision.owner_id,
                "action": decision.action,
                "reason_codes": list(decision.reason_codes),
                "covered_input_fingerprint": decision.identity.covered_input_fingerprint,
            }
            for decision in decisions
        ],
    }
    return ImpactPlan(
        plan_id=_sha256_json(plan_payload),
        requested_scope=requested_scope,
        snapshot=snapshot,
        previous_manifest_path=previous_manifest_path,
        previous_manifest_sha256=previous_manifest_sha256,
        seed_baseline=seed_baseline,
        contracts=contracts,
        decisions=tuple(decisions),
        blockers=tuple(sorted(set(blockers))),
    )


def proof_row_from_child_meta(
    *,
    owner_id: str,
    meta: Mapping[str, Any],
    artifact_fingerprints: Mapping[str, str],
) -> dict[str, Any]:
    identity = meta.get("owner_identity")
    if not isinstance(identity, Mapping):
        raise ValueError(f"{owner_id}:owner_identity_missing")
    result_fingerprint = str(meta.get("result_fingerprint") or "")
    if not result_fingerprint:
        raise ValueError(f"{owner_id}:result_fingerprint_missing")
    proof = ProofArtifactRef(
        artifact_id=f"proof.test-tier-owner.{owner_id}.{result_fingerprint[:16]}",
        producer_route="flowpilot.test-tier.selective-execution",
        command=_portable_command(meta.get("command") or ()),
        result_path=_portable_path(
            str(meta.get("artifacts", {}).get("combined") or "")
        ),
        result_status=str(meta.get("status") or "not_run"),
        exit_code=meta.get("exit_code"),
        started_at=str(meta.get("start_time") or ""),
        finished_at=str(meta.get("end_time") or ""),
        artifact_fingerprints=dict(artifact_fingerprints),
        covered_obligation_ids=tuple(identity.get("covered_obligation_ids") or ()),
        assertion_scope="external_contract",
        current=meta.get("inputs_current") is True,
        route_evidence_current=meta.get("inputs_current") is True,
        progress_only=str(meta.get("status") or "") == "running",
        stale_reasons=(
            ()
            if meta.get("inputs_current") is True
            else ("owner_inputs_changed_during_execution",)
        ),
        metadata={
            "owner_id": owner_id,
            "result_fingerprint": result_fingerprint,
            "descendant_zero_confirmed": meta.get("descendant_zero_confirmed") is True,
        },
    )
    return {
        "owner_id": owner_id,
        "result_status": proof.result_status,
        "result_reused": False,
        "identity": dict(identity),
        "result_fingerprint": result_fingerprint,
        "proof_artifact": proof.to_dict(),
        "reuse_ticket": None,
    }


__all__ = [
    "EVIDENCE_MANIFEST_SCHEMA_VERSION",
    "EXPLICIT_DYNAMIC_INPUT_OWNERS",
    "EXPLICIT_OWNER_OBLIGATION_IDS",
    "IMPACT_PLAN_SCHEMA_VERSION",
    "ImpactPlan",
    "OwnerContract",
    "OwnerDecision",
    "OwnerIdentity",
    "SHARED_CONTROL_PLANE_INPUTS",
    "SHARED_CONTROL_PLANE_OWNER",
    "build_owner_contracts",
    "load_previous_manifest",
    "owner_identity",
    "proof_row_from_child_meta",
    "resolve_impact",
    "sha256_file",
]
