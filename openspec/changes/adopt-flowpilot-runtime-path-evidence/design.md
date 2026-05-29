## Context

FlowGuard 0.34.0 provides `RuntimeNodeContract`, `RuntimeNodeObservation`,
`RuntimePathRun`, and model-test alignment support for runtime path evidence.
FlowPilot's current model-test alignment runner serializes these fields, but the
family plans do not require them yet.

## Goals / Non-Goals

**Goals:**

- Make runtime-path evidence mandatory for FlowPilot's major model-test family
  plans.
- Make each emitted progress line self-identifying for AI review by including
  the FlowGuard model id, model path, runtime node id, source evidence id, and
  obligation binding.
- Preserve existing model/test/source-audit coverage while adding runtime-path
  evidence as a stricter layer.
- Synchronize the installed local FlowPilot skill after the evidence helper is
  updated.

**Non-Goals:**

- No semantic replacement of FlowPilot's ordinary tests.
- No live daemon soak run as a substitute for current foreground checks.
- No broad router restructure, public API contraction, GitHub publication, tag,
  release, deploy, or historical runtime-data deletion.

## Decisions

### Decision: attach runtime nodes at the obligation boundary

Each family plan obligation is the smallest stable FlowGuard leaf currently used
by FlowPilot's model-test alignment layer. The runtime-path helper will create
one required runtime node per obligation and copy that node id into the
obligation's `required_runtime_node_ids` field.

### Decision: progress output must be parseable

Runtime-path observations will use FlowGuard's `format_progress_line()` format
so every line starts with `flowguard.runtime_path` and includes `model=`,
`node=`, `run=`, `model_path=`, `obligation=`, `input_case=`, `state_case=`,
`evidence=`, and `progress=` fields.

### Decision: runtime path is an evidence layer

Runtime-path evidence proves that the declared model/test family exposes a
concrete path binding. It does not claim that a single progress line proves all
semantics; ordinary tests, source-contract audits, family parity checks, and
parent/child FlowGuard checks remain required.

## Validation Plan

1. Validate the OpenSpec change.
2. Run the focused model-test alignment unit tests.
3. Regenerate the model-test alignment result artifact.
4. Run the model-test alignment check script and relevant install/smoke checks.
5. Sync the installed FlowPilot skill and audit local install freshness.
6. Commit the local repository result without pushing or releasing.
