## 1. FlowGuard Model

- [x] 1.1 Add a focused FlowGuard model and runner for Controller process asides.
- [x] 1.2 Cover safe paths and hazards: aside-only wait satisfaction, formal body substitution, decision/evidence misuse, missing-aside blocking, and worker-to-worker leakage.
- [x] 1.3 Run the focused model and inspect the results.

## 2. Runtime And Prompt Surfaces

- [x] 2.1 Add reusable Controller process-aside guidance to runtime prompts/cards.
- [x] 2.2 Add optional `controller_aside` metadata support to packet progress/status and role-output progress/status surfaces.
- [x] 2.3 Ensure Router/controller status preserves asides as Controller-visible process context only and does not treat them as formal evidence or progress authority.
- [x] 2.4 Repeat aside guidance in packet/result/role-output work surfaces so long-running roles see it during active work.

## 3. Tests And Validation

- [x] 3.1 Add focused unit tests for packet process-aside status behavior.
- [x] 3.2 Add focused unit tests for role-output process-aside status behavior.
- [x] 3.3 Add prompt or runtime coverage checks proving aside guidance is present and non-authority wording is enforced.
- [x] 3.4 Run focused tests and relevant install checks.

## 4. Sync And Final Evidence

- [x] 4.1 Run required broader FlowGuard/model regressions, using background artifacts for heavyweight checks.
- [x] 4.2 Sync the repo-owned FlowPilot skill into the local installed copy.
- [x] 4.3 Audit installed skill freshness.
- [x] 4.4 Review peer-agent changes remain preserved and prepare a scoped local git commit.
