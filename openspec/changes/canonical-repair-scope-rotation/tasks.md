## 1. OpenSpec And FlowGuard Grounding

- [x] 1.1 Create proposal, design, spec, and task artifacts for canonical repair
      scope rotation.
- [x] 1.2 Verify real FlowGuard package/schema/project adoption and upgrade the
      project record when required.
- [x] 1.3 Add a focused FlowGuard repair-scope rotation model and runner.

## 2. Runtime Contract

- [x] 2.1 Replace the PM repair decision set with the five current decisions.
- [x] 2.2 Update PM repair decision prompts to describe the five-current-choice
      contract and strict top-level JSON.
- [x] 2.3 Reject old repair decision names instead of translating them.
- [x] 2.4 Require `waive_with_authority` to include an authority reference.
- [x] 2.5 Guard `repair_packet_open` so it requires a fresh current open packet.

## 3. Replacement Scope Mechanics

- [x] 3.1 Implement current-scope repair as replacement node creation plus a
      fresh executable packet.
- [x] 3.2 Implement parent-scope repair as nearest-parent replacement plus
      descendant supersession/quarantine and a fresh executable packet.
- [x] 3.3 Implement route redesign as a gated strict route-plan replacement path.
- [x] 3.4 Keep repair transactions minimal with `source_id`, `blocker_id`, and
      `fresh_packet_id` while preserving audit fields already present.

## 4. Tests And Regressions

- [x] 4.1 Update runtime tests from old decision names to current names.
- [x] 4.2 Add negative tests for removed repair decisions.
- [x] 4.3 Add regression coverage for the June 3 empty-fresh-packet failure.
- [x] 4.4 Add parent-scope and route-redesign tests.

## 5. Validation, Sync, And Git

- [x] 5.1 Run focused FlowGuard repair-scope checks and affected runtime tests.
- [x] 5.2 Run broader model/test checks required by repository guidance.
- [x] 5.3 Rebuild/check FlowGuard topology if model/test registries changed.
- [x] 5.4 Update version and changelog.
- [x] 5.5 Sync installed FlowPilot skill and run install/audit checks.
- [x] 5.6 Commit intended repository changes to local git.
