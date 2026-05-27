## Why

FlowPilot already records material scans, PM package dispositions, reviewer gates, route memory, and final-ledger evidence, but those artifacts are not available through one safe role-facing map. This makes later PM, reviewer, and worker work rely on ad hoc paths or PM prose even when prior material/modeling/self-interrogation outputs should be reusable.

## What Changes

- Add a run-scoped material artifact map that indexes prior material and decision-support artifacts by safe metadata, source paths, hashes, status, and role-readable boundaries.
- Extend PM formal gate packages to cite material-map entries and reviewable source refs without copying sealed worker result bodies.
- Let PM-authored worker/research packets declare bounded material-map entry ids as allowed reads.
- Strengthen reviewer material sufficiency so a clean report must cite concrete checked source paths or runtime-open receipts through the existing packet runtime and packet ledger.
- Link the material map from route memory and final ledger so later PM decisions can find prior materials while still treating route memory as an index, not evidence.

## Capabilities

### New Capabilities
- `material-artifact-map`: Covers the derived run-scoped map for material, modeling, research, self-interrogation, PM package, reviewer, and generated-resource artifacts; access metadata; sealed-body exclusion; packet-authorized worker reads; reviewer source refs; and route-memory/final-ledger linkage.

### Modified Capabilities
- None. Existing packet-open and runtime-ledger requirements remain authoritative; this change adds a material-map capability that references those existing boundaries instead of redefining them.

## Impact

- Affected router source: material packet writers, PM package disposition writers, route-memory refresh, final-ledger source-of-truth entries, packet/runtime contract prompts, and reviewer material sufficiency validation.
- Affected runtime kit: PM material scan, reviewer material sufficiency, worker role cards, PM material understanding, PM prior-path context, and output contract descriptions.
- Affected validation: focused FlowGuard material-map model, targeted router runtime material/modeling tests, packet boundary tests, prompt/card coverage tests, install sync checks, and background FlowGuard regressions where practical.
