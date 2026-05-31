## Why

Recent audit work exposed a model boundary miss in the new FlowPilot runtime:
the runtime and auditors can disagree about the current run pointer, audit code
can crash on unreadable JSON instead of recording weak evidence, and symmetric
role work packets can drift unless packet/result/acceptance obligations are
checked at one shared contract boundary.

This is a bottom-logic repair. It should fix the family once instead of adding
role-specific patches for PM, reviewer, explicit FlowGuard operator, worker, or
system validation/closure outcomes.

## What Changes

- Add a shared current-run resolver that accepts only the current
  `run_id/run_root` pointer schema and rejects implicit or old pointer names.
- Add shared safe JSON/text readers that return structured read findings for
  missing, invalid, or non-UTF-8 evidence instead of crashing audits.
- Add a lightweight control-surface contract validator for current-run packet
  ledgers: all role packets must carry symmetric envelope fields, explicit
  output targets, separate ACK/result/accepted authority, and current
  source-generation evidence.
- Add FlowGuard coverage for why the previous tests missed the class: tests
  checked happy-path route behavior after materials were already projected, not
  current-run resolution, evidence-read failure, or symmetric envelope drift.

## Impact

- Affected code: `skills/flowpilot/assets/ai_project_runtime/`, focused audit
  adapters under `simulations/`, and focused tests.
- Affected behavior: current-run loading and live audits use one resolver;
  unreadable evidence produces findings instead of exceptions; packet contract
  drift is reported before completion confidence.
- Non-goals: no old monitor UI, no fixed-role requirement, no sealed-body reads
  by Controller/auditors, and no broad router rewrite.
