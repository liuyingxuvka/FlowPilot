## 1. Contract And Prompt Design

- [x] 1.1 Update PM planning and node-acceptance cards so PM must write rich high-standard requirements, acceptance rows, route nodes, node criteria, references, risks, and verification intent before worker execution.
- [x] 1.2 Update Worker, Reviewer, and FlowGuard cards so backstage roles consult the current user/PM standard, perform in-scope high-quality completion or challenge, and escalate scope/route/authority changes through existing fields.
- [x] 1.3 Update reviewer cards so local-only node plans, weak worker results, missing relevant references, and source-intent dilution block through existing blocker and repair fields.

## 2. Existing-Field Runtime Contract Projection

- [x] 2.1 Inspect current packet/result contracts and add only existing-field requiredness or non-empty array declarations needed for high-standard planning and node context.
- [x] 2.2 Keep runtime/router enforcement mechanical: missing field, empty required array, wrong type, invalid finite value, forbidden alias, stale/current-run mismatch, unsupported command, or wrong active authority.
- [x] 2.3 Avoid new fields, defaults, compatibility aliases, semantic runtime scoring, or fallback acceptance paths.

## 3. Test And Model Coverage

- [x] 3.1 Add prompt/card coverage tests for PM high-standard planning and global-standard references in Worker, Reviewer, and FlowGuard cards.
- [x] 3.2 Add AI contract projection tests for every newly declared existing required/non-empty field family.
- [x] 3.3 Add contract-exhaustion/fake-AI tests for Cartesian missing, empty, wrong-type, forbidden-alias, invalid-value, and representative valid packages.
- [x] 3.4 Add or update FlowGuard planning-quality and fake-AI replay models for local-only context, low-standard planning, missing existing fields, and corrected retry behavior.

## 4. Verification And Sync

- [x] 4.1 Run focused pytest checks named in `verification-contract.yaml` and fix failures.
- [x] 4.2 Run FlowGuard model checks for planning quality, contract exhaustion, and fake-AI runtime replay.
- [x] 4.3 Rebuild and check the FlowGuard project topology after prompt/runtime/test/model changes.
- [x] 4.4 Sync the installed local FlowPilot skill/runtime from the repository and run local install audit checks.
- [x] 4.5 Run the OpenSpec verification contract and mark this task list complete only after required evidence passes.

## 5. Final Review

- [x] 5.1 Inspect git diff for unrelated or peer changes and preserve anything not owned by this implementation.
- [x] 5.2 Perform KB postflight and record a structured observation if this task exposes a reusable route, prompt, test, or process lesson.
- [x] 5.3 Report the implemented changes, checks run, known skipped checks if any, and remaining risk boundary in Chinese.
