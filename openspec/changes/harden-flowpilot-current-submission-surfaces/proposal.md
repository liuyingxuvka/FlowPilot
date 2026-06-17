# Harden FlowPilot Current Submission Surfaces

## Why

FlowPilot's current runtime path is `flowpilot_new.py` with packet, lease, and
current handoff contracts. Recent repair work added an `open-packet`
submission checklist, but several role-facing cards and generated payload
contracts still expose older command surfaces or short-field examples. Some
router helpers also still accept old alias fields as fallbacks.

That creates information asymmetry: the model can declare a current contract,
while the role sees an incomplete checklist, an outdated command, or an alias
that appears valid. The result is repeated bug repair instead of one clear
path.

## What Changes

- Extend `open-packet` `submission_checklist` projection from the full current
  handoff contract, including report fields, branch shapes, forbidden fields,
  material manifests, and required read obligations.
- Remove role-facing instructions that name obsolete live command paths or
  lower-level role-output helper commands for current packet submission.
- Reject behavior-bearing old alias fields in PM disposition, formal gate,
  material-sufficiency, and request packet helpers instead of falling back to
  them.
- Expand prompt/card validation so current role-facing generated Python
  contract sources are scanned for forbidden old command surfaces.
- Bind the new field lifecycle and prompt-surface obligations to focused
  tests, FlowGuard checks, install sync, and topology refresh.

## Non-Goals

- Do not redesign FlowPilot's packet protocol.
- Do not add a second checklist, ledger, router, or compatibility layer.
- Do not remove historical archive documentation or internal legacy runtime
  code that is not exposed as a current role-facing path.
- Do not overwrite peer-agent changes in unrelated files.

