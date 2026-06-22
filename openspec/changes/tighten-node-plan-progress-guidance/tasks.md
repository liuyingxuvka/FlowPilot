## 1. Prompt/Card Updates

- [x] 1.1 Update PM node acceptance guidance to require concrete current check surfaces, status vocabulary, and expected failure shapes without adding node-context fields.
- [x] 1.2 Update Reviewer node acceptance plan review guidance to block abstract worker-ready plans while preserving plan-stage evidence boundaries.
- [x] 1.3 Update Controller core, resume, action-ledger prompt, and launcher guidance so legitimate user-facing status updates normally include runtime-owned `progress_fraction.display`.

## 2. Regression Coverage

- [x] 2.1 Add card instruction coverage for PM concrete check-surface guidance and Reviewer abstract-plan blocking guidance.
- [x] 2.2 Add card instruction coverage for Controller progress-fraction reporting cadence and quiet-internal-patrol boundary.
- [x] 2.3 Extend focused planning-quality model coverage for node plans that omit current checker/status/failure-shape details.

## 3. Validation

- [x] 3.1 Run OpenSpec strict validation for this change.
- [x] 3.2 Run focused prompt/card, planning-quality, prework/order, and controller patrol checks.
- [x] 3.3 Run broader FlowGuard/process checks required by prompt/process changes and inspect background artifacts when checks run in background.

## 4. Sync And Completion

- [x] 4.1 Rebuild and check FlowGuard project topology if prompt/test/model surfaces changed.
- [x] 4.2 Sync the repo-owned FlowPilot install and verify local install freshness.
- [x] 4.3 Update local version/changelog/git evidence without reverting peer-agent work.
