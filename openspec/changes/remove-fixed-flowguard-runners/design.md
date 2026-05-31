## Context

The runtime should dispatch FlowGuard work, not prescribe repository-specific
runner names. A FlowGuard operator packet already contains the target result,
the modeled target, node context when available, and a run-local evidence root.
That is enough for the operator to inspect the project, reuse relevant models,
run relevant checks, or create scoped evidence for the current packet.

## Goals / Non-Goals

**Goals:**

- Keep FlowPilot as the packet, lease, ledger, and evidence-root authority.
- Let FlowGuard operator own validation strategy selection for the packet.
- Prevent absent repo-specific runners from becoming a built-in hard blocker.
- Preserve the rule that formal-run evidence belongs under the packet's
  run-local evidence root unless a baseline refresh is explicitly requested.
- Correctly classify structured blocked FlowGuard outcomes.

**Non-Goals:**

- Do not remove this repository's real Meta/Capability runners or their
  validation role for FlowPilot's own source repo.
- Do not weaken Reviewer gates; reviewers still inspect the evidence report
  and may block weak, stale, missing, or wrongly scoped evidence.
- Do not make runtime infer that every nested report with `ok=true` is enough
  for completion; normal review and closure checks still apply.

## Decisions

### Decision: Do not emit fixed runner recommendations

FlowGuard operator packets will retain `evidence_output_policy` but omit
`recommended_runner_commands`. The instruction remains short and tells the
operator to select or create suitable FlowGuard evidence.

Rationale: The runtime cannot know every target repository's model layout. A
fixed recommendation turns one repository's validation scripts into a global
assumption. The FlowGuard operator, PM, and Reviewer already have the packet
context needed to decide what evidence is appropriate.

### Decision: Preserve baseline protection as policy, not runner routing

The packet may still say tracked `simulations/*_results.json` baselines are
forbidden unless the packet explicitly requests a baseline refresh.

Rationale: This protects source-controlled baseline files from formal-run
evidence churn without telling the operator which runner to use.

### Decision: Parse FlowGuard blocked signals from common structured fields

The runtime will recognize `verdict` alongside existing outcome fields. It will
also treat a nested mapping `flowguard_report: { "ok": false }` as blocking
even if nearby top-level wording looks optimistic.

Rationale: FlowGuard reports commonly use verdict-like language and `ok`
summary booleans. A failing nested report must not become an outer pass just
because the field name is not in the parser allowlist.

## Validation Strategy

- Unit-test generated FlowGuard operator packet bodies to assert no
  `recommended_runner_commands` are present and run-local evidence policy
  remains present.
- Unit-test semantic outcome parsing for `verdict: blocked` and
  `flowguard_report.ok=false`.
- Run the focused FlowPilot runtime tests and semantic outcome model check.
- Run project-level FlowGuard/topology checks before install sync.
- Synchronize the installed FlowPilot skill and audit installed/source
  freshness.
