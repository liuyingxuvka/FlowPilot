"""Known-bad cases for FlowPilot model-test alignment checks."""

from __future__ import annotations

from typing import Any

from flowpilot_model_test_alignment_common import *

def _known_bad_cases() -> list[dict[str, Any]]:
    obligation = _obligation(
        "known_bad.required_obligation",
        obligation_type="hazard",
        description="Synthetic obligation used only to prove the FlowGuard alignment reviewer rejects bad evidence.",
        required_test_kinds=(HAPPY,),
    )
    path = "tests/test_flowpilot_model_test_alignment.py"
    command = "python -m unittest tests.test_flowpilot_model_test_alignment"
    code_contract = CodeContract(
        "known_bad.required_contract",
        path=path,
        symbol="FlowPilotModelTestAlignmentTests",
        implements_obligations=("known_bad.required_obligation",),
    )
    return [
        {
            "name": "missing_evidence",
            "expected_codes": ["missing_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_missing_evidence",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(),
            ),
        },
        {
            "name": "stale_evidence",
            "expected_codes": ["stale_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_stale_evidence",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(
                    _evidence(
                        "known_bad.stale",
                        test_name="synthetic stale evidence",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        code_contracts=("known_bad.required_contract",),
                        evidence_current=False,
                        stale_reasons=("model obligation changed after evidence was recorded",),
                    ),
                ),
            ),
        },
        {
            "name": "progress_only_background_evidence",
            "expected_codes": ["test_evidence_not_passing"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_progress_only",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(
                    _evidence(
                        "known_bad.progress_only",
                        test_name="synthetic background check with progress output only",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        code_contracts=("known_bad.required_contract",),
                        result_status=RUNNING,
                    ),
                ),
            ),
        },
        {
            "name": "overclaim_model_confidence",
            "expected_codes": ["test_overclaims_model_confidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_overclaim",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(
                    _evidence(
                        "known_bad.overclaim",
                        test_name="synthetic evidence that overclaims full model confidence",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        code_contracts=("known_bad.required_contract",),
                        overclaims_model_confidence=True,
                    ),
                ),
            ),
        },
        {
            "name": "orphan_evidence",
            "expected_codes": ["orphan_test_evidence"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_orphan",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(
                    _evidence(
                        "known_bad.orphan",
                        test_name="synthetic evidence without obligation binding",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=(),
                    ),
                ),
            ),
        },
        {
            "name": "duplicate_same_kind_evidence",
            "expected_codes": ["duplicate_test_evidence_owner"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_duplicate",
                obligations=(obligation,),
                code_contracts=(code_contract,),
                test_evidence=(
                    _evidence(
                        "known_bad.duplicate.first",
                        test_name="synthetic duplicate evidence first owner",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        code_contracts=("known_bad.required_contract",),
                    ),
                    _evidence(
                        "known_bad.duplicate.second",
                        test_name="synthetic duplicate evidence second owner",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.required_obligation",),
                        code_contracts=("known_bad.required_contract",),
                    ),
                ),
            ),
        },
        {
            "name": "missing_runtime_path_evidence",
            "expected_codes": ["runtime_node_missing_observation"],
            "plan": ModelTestAlignmentPlan(
                model_id="known_bad_runtime_path_missing",
                obligations=(
                    ModelObligation(
                        "known_bad.runtime_path_required",
                        obligation_type="hazard",
                        description="Synthetic obligation proving runtime-path nodes cannot be skipped when required.",
                        required_test_kinds=(HAPPY,),
                        required_runtime_node_ids=("known_bad.runtime_path.node",),
                    ),
                ),
                code_contracts=(
                    CodeContract(
                        "known_bad.runtime_path_contract",
                        path=path,
                        symbol="FlowPilotModelTestAlignmentTests",
                        implements_obligations=("known_bad.runtime_path_required",),
                    ),
                ),
                test_evidence=(
                    _evidence(
                        "known_bad.runtime_path.has_test",
                        test_name="synthetic evidence without runtime path observation",
                        path=path,
                        command=command,
                        test_kind=HAPPY,
                        covers=("known_bad.runtime_path_required",),
                        code_contracts=("known_bad.runtime_path_contract",),
                    ),
                ),
                require_runtime_path_evidence=True,
            ),
        },
    ]


def _source_known_bad_cases() -> list[dict[str, Any]]:
    command = "python -m unittest tests.test_flowpilot_model_test_alignment"
    return [
        {
            "name": "missing_python_symbol",
            "expected_codes": ["source_contract_missing_symbol"],
            "code_contracts": (
                CodeContract(
                    "source_bad.missing",
                    path="synthetic_source.py",
                    symbol="missing_symbol",
                ),
            ),
            "test_evidence": (),
            "source_by_path": {
                "synthetic_source.py": "def other_symbol():\n    return 1\n",
            },
        },
        {
            "name": "internal_path_only_test",
            "expected_codes": [
                "source_test_internal_path_only",
                "source_test_missing_code_contract_call",
            ],
            "code_contracts": (
                CodeContract(
                    "source_bad.foo",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (
                TestEvidence(
                    "source_bad.internal_path",
                    test_name="test_foo",
                    path="test_synthetic_source.py",
                    command=command,
                    result_status=PASSED,
                    covered_code_contracts=("source_bad.foo",),
                ),
            ),
            "source_by_path": {
                "synthetic_source.py": "def foo(value):\n    return value\n",
                "test_synthetic_source.py": "def test_foo():\n    assert 1 == 1\n",
            },
        },
        {
            "name": "missing_external_assertion",
            "expected_codes": [
                "source_test_internal_path_only",
                "source_test_missing_external_assertion",
            ],
            "code_contracts": (
                CodeContract(
                    "source_bad.foo",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (
                TestEvidence(
                    "source_bad.no_assert",
                    test_name="test_foo",
                    path="test_synthetic_source.py",
                    command=command,
                    result_status=PASSED,
                    covered_code_contracts=("source_bad.foo",),
                ),
            ),
            "source_by_path": {
                "synthetic_source.py": "def foo(value):\n    return value\n",
                "test_synthetic_source.py": "def test_foo():\n    foo(1)\n",
            },
        },
        {
            "name": "extra_side_effect",
            "expected_codes": ["source_contract_extra_side_effect"],
            "code_contracts": (
                CodeContract(
                    "source_bad.extra_effect",
                    path="synthetic_source.py",
                    symbol="foo",
                ),
            ),
            "test_evidence": (),
            "source_by_path": {
                "synthetic_source.py": (
                    "def write_json(payload):\n"
                    "    return None\n\n"
                    "def foo(value):\n"
                    "    write_json({'value': value})\n"
                    "    return value\n"
                ),
            },
        },
    ]
