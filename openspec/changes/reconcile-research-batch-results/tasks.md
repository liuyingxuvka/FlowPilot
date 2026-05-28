## 1. Specification and Modeling

- [x] 1.1 Add OpenSpec requirements for research batch durable result reconciliation and stale reminder suppression.
- [x] 1.2 Confirm real FlowGuard import and keep the control-plane state consistency model covering the observed research join miss.

## 2. Router Reconciliation

- [x] 2.1 Extend the existing durable wait evidence reconciliation path so research `results_joined` records `worker_research_report_returned`.
- [x] 2.2 Keep the research PM relay path owned by the existing `relay_research_result_to_pm` action and receipt registry.
- [x] 2.3 Preserve sealed body boundaries by using result envelopes, hashes, batch ids, packet ids, and next-recipient checks only.

## 3. Tests and Evidence

- [x] 3.1 Add focused router runtime regression coverage for research result envelopes that already exist before the worker return event is manually recorded.
- [x] 3.2 Run focused Python/unit checks and FlowGuard control-plane checks.
- [x] 3.3 Run or launch heavyweight Meta/Capability checks using documented background artifacts and inspect completion evidence.

## 4. Sync and Review

- [x] 4.1 Sync repository-owned FlowPilot assets into the local installed skill/runtime copy.
- [x] 4.2 Run install audit/checks against the local installed copy.
- [x] 4.3 Review git status and preserve peer-agent changes; only stage or commit if the intended scope is safe.
