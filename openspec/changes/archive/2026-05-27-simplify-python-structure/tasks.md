## 0. Baseline And Guardrails

- [x] 0.1 Confirm local `main`, clean/known worktree state, FlowGuard import, and no active coordination protocol.
- [x] 0.2 Preserve rollback evidence with the current commit, local backup directory, file-size/function-size baseline, and validation command list.
- [x] 0.3 Update and run the structural FlowGuard guard for this simplification pass.
- [x] 0.4 Validate the OpenSpec change strictly before production-code edits.

## 1. Duplicate Wrapper Cleanup

- [x] 1.1 Convert `scripts/flowpilot_user_flow_diagram.py` into a thin wrapper around the skill asset source of truth.
- [x] 1.2 Add or update wrapper/source-freshness checks so the duplicate logic cannot drift back in.
- [x] 1.3 Run user-flow diagram focused tests and install checks for the wrapper slice.

## 2. Packet Runtime Structure

- [x] 2.1 Split packet runtime schema/path/contract helpers behind the existing `packet_runtime.py` facade.
- [x] 2.2 Split packet ledger and relay helpers behind the existing facade.
- [x] 2.3 Split active-holder/session/reviewer helpers behind the existing facade.
- [x] 2.4 Preserve the packet runtime CLI and public import surface.
- [x] 2.5 Run packet runtime, output-contract, and install checks.

## 3. Install Check Structure

- [x] 3.1 Move file/manifest/runtime/docs/result check groups from `scripts/check_install.py` into helper modules.
- [x] 3.2 Preserve `scripts/check_install.py --json` output shape, severity semantics, and caller compatibility.
- [x] 3.3 Run install, public-release, and installer self-check paths.

## 4. Meta And Capability Model Phase Structure

- [x] 4.1 Split the largest Meta model phase helpers into focused modules without changing model semantics.
- [x] 4.2 Split the largest Capability model phase helpers into focused modules without changing model semantics.
- [x] 4.3 Run structural guard plus Meta and Capability checks through direct or background evidence.

## 5. Router Hotspot Structure

- [x] 5.1 Split router external-event intake helpers behind `_record_external_event_unchecked`.
- [x] 5.2 Split router event identity, ACK preconsume, quarantine, and commit helpers without changing event names or state shape.
- [x] 5.3 Split remaining low-risk controller action application helpers behind `apply_controller_action`.
- [x] 5.4 Run router focused tests for controller, ACK/return, route mutation, terminal, closure, cards, packets, resume, dispatch gate, and startup daemon domains.

## 6. Router Runtime Test Structure

- [x] 6.1 Move remaining high-value tests from the aggregate router runtime file into domain entry files.
- [x] 6.2 Keep the aggregate test entrypoint compatible during migration.
- [x] 6.3 Run the domain suites and any remaining aggregate compatibility tests.

## 7. Final Validation, Sync, And Local Git

- [x] 7.1 Run final focused Python compile and regression checks for touched files.
- [x] 7.2 Run install sync, install check, installed freshness audit, and public-boundary/privacy checks.
- [x] 7.3 Update HANDOFF, README, FlowGuard adoption log, and baseline notes with final structure and validation evidence.
- [x] 7.4 Commit the validated result on local `main` and leave no extra local work branches.
- [x] 7.5 Run KB postflight and record reusable maintenance lessons.

## 8. Meta/Capability Evidence Layering

- [x] 8.1 Extend the OpenSpec artifacts to make thin-parent routine evidence and background full-regression release evidence explicit.
- [x] 8.2 Drive model hierarchy inventory from `flowpilot_parent_responsibility_ledger.json` instead of a duplicate hard-coded partition map.
- [x] 8.3 Add FlowGuard hierarchy hazards for hidden release obligations and full regression incorrectly blocking routine thin-parent confidence.
- [x] 8.4 Run focused hierarchy/thin-parent validation and launch full Meta/Capability regressions through the background artifact contract.
