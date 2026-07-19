# Fake Authority Residue Classification

Date: 2026-07-10

Scope: current `flowpilot_core_runtime` fake E2E, black-box fake-project
rehearsal, current handoff/checklist projection, and directly related tests.
This classification does not declare unrelated packet-runtime subsystems
deleted.

## Search

The focused residue search covered:

- `black_box_flowpilot.current_handoff_contract.v1` and
  `black_box_flowpilot.submission_checklist.v1`;
- the retired fake-project symbols `current_contract_body_for_packet`,
  `_high_standard_contract_body`, and `_generic_current_result_body`;
- direct fake use of `_submission_checklist_from_current_handoff_contract`;
- direct fake use of `minimal_valid_shape_for_family`;
- conditional packet-body field names, `daemon_replay`, and retired role/source
  labels.

## Classification

| Remaining surface | Classification | Disposition |
|---|---|---|
| v1 handoff/checklist strings in `tests/test_flowpilot_new_entrypoint.py` | forbidden negative | They are asserted absent from current prompt/card output and cannot authorize execution. |
| `_submission_checklist_from_current_handoff_contract` in `flowpilot_new_role_commands.py` | current runtime owner | It is the internal writer called only by public `open_packet`; core fake E2E and fake project do not call it directly. |
| `minimal_valid_shape_for_family` in `packet_result_contracts.py` and current runtime contract construction | current registry owner | Runtime may build the envelope handoff from the registry. Fake positive payloads do not call the registry; they consume the public checklist projection. |
| `minimal_valid_shape_for_family` in ordinary tests or formal structural models | test/model fixture | It may test registry semantics or enumerate model cells but is not fake public-path execution evidence by itself. |
| `_high_standard_contract_body` in `tests/test_flowpilot_high_standard_control_flow.py` | test-only direct-runtime fixture | The symbol is outside the active fake E2E/fake-project generators. It cannot satisfy the black-box fake-project or public-open proof rows. |
| retired fake-project symbol names in `tests/test_flowpilot_fake_project_rehearsal.py` | forbidden negative | Tests assert those callable alternate generators are absent. |
| `conditional_required_result_body_sections` and `conditional_required_body_fields` in the separate `packet_runtime` contract catalog | scoped separate subsystem | They are not read by the current black-box fake path. Within the current-handoff authority boundary, packet-body conditional mechanics are blocked and recorded in FieldLifecycleMesh. |
| `daemon_replay` and retired role aliases in the PPA/FieldLifecycle model and role/source tests | historical/forbidden negative | They have no current readers or writers and use blocked disposition. |
| canonical `project_manager` labels in the separate packet-runtime/card catalog | current separate role vocabulary | They are not treated as aliases for the black-box current-runtime `pm` responsibility and are outside this fake-authority boundary. |

## Active-Path Result

The active core fake E2E contains public `dispatch_current_role`, `ack`,
`open_packet`, and `submit_result` calls. It contains no direct private
checklist-builder call, registry minimal-shape call, host lease call, or host
submit call.

The active fake-project generator exposes only
`current_contract_body_from_open_result`. Every positive branch first validates
the full public open result with `ContractDrivenFakeAIResponder` and starts from
its checklist-derived legal payload. Packet bodies remain semantic material;
they cannot provide a mechanical result shape.

## Claim Boundary

This residue pass proves removal or classification inside the assigned fake
authority boundary. It does not prove that unrelated legacy packet-runtime
contracts are unused across the entire repository, and it does not replace the
full formal-AI, TestMesh, release, or installation gates.
