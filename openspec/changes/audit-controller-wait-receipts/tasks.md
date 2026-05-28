## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Validate OpenSpec artifacts and confirm the new capability scope is separate from quiet standby reporting.
- [x] 1.2 Verify real FlowGuard import and add focused wait-audit model coverage for all wait classes.
- [x] 1.3 Run the focused wait-audit model checks before production code changes.

## 2. Runtime Implementation

- [x] 2.1 Add a metadata-only Controller wait receipt auditor that scans formal receipt surfaces without sealed body reads.
- [x] 2.2 Wire the audit into Controller standby and patrol snapshots for all active wait states.
- [x] 2.3 Expose clear classifications for no formal return, formal return ready, stale control plane, missing next-action notice, aside-only claim, and malformed evidence.
- [x] 2.4 Keep `controller_aside` non-authoritative while allowing it to trigger formal receipt checks.

## 3. Prompts, Cards, And User Status

- [x] 3.1 Update Controller role card and table prompt wording so every wait wakeup checks formal receipts before continuing to wait.
- [x] 3.2 Update user-status wording to explain audited wait states plainly without sealed content or work-quality judgments.

## 4. Tests And Validation

- [x] 4.1 Add focused unit tests for wait-audit classifications and sealed-body boundary preservation.
- [x] 4.2 Add standby/patrol integration tests proving active waits include audit metadata and ready/stuck audit results preempt quiet waiting.
- [x] 4.3 Run focused unit tests for wait audit, standby, controller boundaries, prompt store, and process asides.
- [x] 4.4 Run heavyweight meta and capability checks in documented background logs and inspect completion artifacts.

## 5. Install Sync And Git Hygiene

- [x] 5.1 Sync repository FlowPilot assets into the local installed skill.
- [x] 5.2 Run install audit/checks against the local installed copy.
- [x] 5.3 Review git status, preserve peer-agent work, and only stage/commit the intended combined scope when safe.
