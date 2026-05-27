## 1. Diagnostic Triage Metadata

- [x] 1.1 Add severity, surface owner, release relevance, repair type, dedupe key, and priority scoring to full diagnostic findings.
- [x] 1.2 Add deduplicated actionable summary fields and aggregate counts by severity and repair type.
- [x] 1.3 Extend model-test-code alignment tests to assert the new diagnostic schema and known-bad classifications.
- [x] 1.4 Update diagnostic documentation to explain the triage fields and repair workflow.

## 2. Source Contract Coverage

- [x] 2.1 Add facade parity/external-contract tests for packet runtime public exports.
- [x] 2.2 Add or strengthen external-contract tests for router receipt and PM-role owner modules.
- [x] 2.3 Add or strengthen external-contract tests for terminal/runtime closure and daemon lock/status/queue surfaces.
- [x] 2.4 Teach the diagnostic to recognize the new external-contract evidence and avoid counting internal-only tests as full coverage.

## 3. CLI Entrypoint Coverage

- [x] 3.1 Add fast CLI behavior tests for installer, local install sync, and release audit entrypoints.
- [x] 3.2 Add fast CLI behavior tests for test-tier list/dry-run/background child/supervisor option paths.
- [x] 3.3 Add fast CLI behavior tests for packet, output, and lifecycle script entrypoints.
- [x] 3.4 Teach the diagnostic to account for public script entrypoint evidence.

## 4. Background Evidence Reliability

- [x] 4.1 Add BOM-tolerant meta JSON reading for background artifact inspection.
- [x] 4.2 Classify pass, failed, running, incomplete, stale, progress-only, and local-only release proof states.
- [x] 4.3 Add report-only audit coverage for historical background artifact roots without deleting or mutating them.
- [x] 4.4 Add tests proving progress-only artifacts cannot count as pass and `--skip-url-check` release evidence is local-only.

## 5. Structure Split Repair Planning

- [x] 5.1 Review current split candidates and mark each as immediate or deferred with concrete owner and reason metadata.
- [x] 5.2 Safely split any isolated candidate that does not overlap recent owner-module polish or peer work.
- [x] 5.3 Record deferred split candidates in the diagnostic as actionable repair items, not completed work.

## 6. Verification, Sync, and Evidence

- [x] 6.1 Regenerate the model-test-code diagnostic result JSON.
- [x] 6.2 Run focused unit/pytest checks for changed diagnostics, boundary tests, CLI tests, and background evidence helpers.
- [x] 6.3 Run OpenSpec strict validation for this change.
- [x] 6.4 Run practical background test-tier validation and inspect final artifacts, not progress logs only.
- [x] 6.5 Sync the local installed FlowPilot skill and verify repo/install/git version consistency.
- [x] 6.6 Record FlowGuard adoption evidence and KB postflight observation if reusable lessons were exposed.
