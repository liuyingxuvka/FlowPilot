## 1. OpenSpec And FlowGuard

- [x] 1.1 Add OpenSpec deltas for role-authored PM-visible summaries and PM packet propagation.
- [x] 1.2 Add focused FlowGuard regression coverage for missing summary blocking and PM summary handoff.

## 2. Runtime

- [x] 2.1 Require `pm_visible_summary` for formal non-PM role result bodies.
- [x] 2.2 Reissue the same current packet family when the summary contract fails.
- [x] 2.3 Add `recent_role_report_summary` to PM packets from role-authored summaries only.
- [x] 2.4 Prefer structured `required_repair` guidance in PM repair-decision packets.
- [x] 2.5 Add `authorized_result_reads` grants, `open-result`, and result-body open receipts.
- [x] 2.6 Block required-role submits until required authorized result bodies are opened.
- [x] 2.7 Inherit blocking-report reads into PM repair packets and fresh repair work packets.

## 3. Prompt Cards

- [x] 3.1 Update worker, FlowGuard operator, and Reviewer role guidance to require `pm_visible_summary`.
- [x] 3.2 Update PM guidance to consume `recent_role_report_summary`.
- [x] 3.3 Update role and packet guidance for `authorized_result_reads`/`open-result`.

## 4. Validation And Sync

- [x] 4.1 Add focused unit tests.
- [x] 4.2 Run focused runtime tests and FlowGuard checks.
- [x] 4.3 Run install sync/check and verify installed skill matches source.
- [ ] 4.4 Record FlowGuard adoption evidence and KB postflight.
