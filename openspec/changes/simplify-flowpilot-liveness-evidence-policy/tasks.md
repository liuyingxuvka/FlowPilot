## 1. OpenSpec And FlowGuard Planning

- [x] 1.1 Verify real FlowGuard package/adoption status and current project
  topology before implementation.
- [x] 1.2 Record the development-process route, field-lifecycle route, and
  TestMesh route boundaries for this change.
- [x] 1.3 Keep the change current-contract only: no compatibility mode, no
  fallback parser, and no old-field translation.

## 2. Runtime Liveness Evidence Policy

- [x] 2.1 Change runtime wait configuration to 5-minute patrol, 5-minute ACK
  reminder, 10-minute ACK replacement, 10-minute progress reminder, and
  30-minute progress replacement.
- [x] 2.2 Replace host-liveness status based wait decisions with ACK/progress
  evidence-age decisions in the lifecycle guard.
- [x] 2.3 Generate fixed runtime-owned ACK and progress reminder duties for
  Controller.
- [x] 2.4 Ensure valid progress after a stale wait positively recovers the same
  active lease and cannot be overridden by old timeout state.

## 3. Old Field And Command Deletion

- [x] 3.1 Remove `timeout_unknown` from current runtime status enums, command
  payloads, prompt surfaces, and positive tests.
- [x] 3.2 Delete or reject current `host_liveness` command paths that only
  support the old wait authority.
- [x] 3.3 Remove `liveness_status`, `last_liveness_status`,
  `host_liveness_history`, and `host_liveness_reports` from current wait
  authority and field lifecycle outputs.
- [x] 3.4 Leave old names only in forbidden/deleted lists, negative tests, or
  historical labels.

## 4. Prompt And Packet Contract Updates

- [x] 4.1 Update every background role card with the same `progress +1`
  instruction and metadata-only restriction.
- [x] 4.2 Update packet identity and role-output progress contracts so packets
  carry the exact progress command and expected response to runtime reminders.
- [x] 4.3 Remove current prompt instructions that tell Controller or roles to
  create `timeout_unknown` or host-liveness reports.

## 5. FlowGuard Models And Field Lifecycle

- [x] 5.1 Update lifecycle guard and process liveness models to prove the
  ACK/progress evidence ladder.
- [x] 5.2 Update role recovery/liveness and resume models so old timeout
  states are deleted or negative-only.
- [x] 5.3 Update FieldLifecycleMesh sources/results to classify old liveness
  fields as deleted/forbidden instead of current.
- [x] 5.4 Update model-test alignment or field contract rows affected by the
  field deletion.

## 6. Test And Fake-Agent Cartesian Coverage

- [x] 6.1 Add lifecycle guard unit tests for 5/10-minute ACK thresholds and
  10/30-minute progress thresholds.
- [x] 6.2 Add positive recovery tests for progress after reminder and stale
  timeout residue.
- [x] 6.3 Add negative tests rejecting `timeout_unknown`, host-liveness timeout,
  and bounded-wait timeout as current wait inputs.
- [x] 6.4 Extend fake-agent rehearsal with Cartesian ACK/result/progress/time/
  reminder/legacy-pollution cases.
- [x] 6.5 Add prompt/card coverage tests proving every role sees the unified
  progress instruction.

## 7. Validation, Install Sync, And Git

- [x] 7.1 Run focused lifecycle, prompt, fake-agent, field, and model tests.
- [x] 7.2 Run affected FlowGuard model checks and update result artifacts.
- [x] 7.3 Run meta and capability checks through the background log contract
  and inspect final artifacts.
- [x] 7.4 Rebuild/check the FlowGuard project topology if model/test/code
  ownership surfaces changed.
- [x] 7.5 Sync the local installed `flowpilot` skill and run install audits.
- [x] 7.6 Commit the scoped local git changes without reverting peer-agent work.
