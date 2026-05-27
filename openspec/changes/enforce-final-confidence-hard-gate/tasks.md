## 1. Final Confidence Gate

- [x] 1.1 Add a final confidence aggregation module and CLI under `simulations/`.
- [x] 1.2 Require current live-run audit evidence and block skipped or failing live audit payloads.
- [x] 1.3 Require `full_coverage_ok=true` from model-test alignment before broad confidence.
- [x] 1.4 Consume known-friction defect-family and Risk Evidence Ledger decisions.

## 2. Test-Tier Exposure

- [x] 2.1 Add a named `final-confidence` test tier.
- [x] 2.2 Keep routine tier semantics scoped so fast/integration success does not imply final confidence.

## 3. Verification

- [x] 3.1 Add focused tests for full pass, skipped live audit, failed live audit, and incomplete full coverage.
- [x] 3.2 Run OpenSpec validation and focused Python tests.
- [x] 3.3 Run the final confidence gate against current repository evidence and report any intentional blockers.

## 4. Sync and Closeout

- [x] 4.1 Sync repository-owned FlowPilot skill into the local installed skill.
- [x] 4.2 Run install audit and install check after sync.
- [x] 4.3 Start heavyweight model regressions in the background and inspect final artifact status.
- [x] 4.4 Record FlowGuard adoption evidence and KB postflight.
